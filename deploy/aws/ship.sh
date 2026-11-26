#!/usr/bin/env bash
# Quiet Camps on AWS (ADR 0006): CloudFront in front of the web on S3 and the API on Lambda.
#
#   deploy/aws/ship.sh bootstrap   # once: the ECR repository for the API image
#   deploy/aws/ship.sh cert        # once, with DOMAIN set: its certificate (us-east-1)
#   deploy/aws/ship.sh deploy      # build and push the image, update the stack, upload the web
#   deploy/aws/ship.sh status      # the stacks, the site's /api/health, this month's cost
#   deploy/aws/ship.sh teardown    # delete everything this script made
#
# Settings come from deploy/aws/.env (copy .env.example). The database is loaded separately,
# with publish-db.sh. Everything is tagged Project=quiet-camps.
set -euo pipefail
cd "$(dirname "$0")/../.."

# shellcheck source=/dev/null
source deploy/aws/.env
: "${AWS_PROFILE:?set it in deploy/aws/.env}"
: "${NEON_DATABASE_URL:?set it in deploy/aws/.env}"
: "${ORIGIN_SECRET:?set it in deploy/aws/.env: openssl rand -hex 32}"
export AWS_PROFILE AWS_REGION=ap-southeast-2

STACK=quiet-camps
ECR_STACK=quiet-camps-ecr
CERT_STACK=quiet-camps-cert # in us-east-1: CloudFront only takes certificates from there
DOMAIN=${DOMAIN:-}
TAGS=(Project=quiet-camps)

output() { # output STACK KEY
  aws cloudformation describe-stacks --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text
}

# The certificate's ARN when DOMAIN is set, else empty (CloudFront's own domain).
certificate() {
  [[ -n "$DOMAIN" ]] || return 0
  aws cloudformation describe-stacks --region us-east-1 --stack-name "$CERT_STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='CertificateArn'].OutputValue" --output text
}

bootstrap() {
  aws cloudformation deploy --stack-name "$ECR_STACK" --template-file deploy/aws/ecr.yaml \
    --tags "${TAGS[@]}"
  output "$ECR_STACK" RepositoryUri
}

# The certificate for DOMAIN. ACM checks a CNAME at the domain's DNS host, which may not be
# AWS: this prints the record to add, then waits (up to an hour) until ACM has seen it.
cert() {
  : "${DOMAIN:?set it in deploy/aws/.env, e.g. quiet-camps.example.com}"
  if ! aws cloudformation describe-stacks --region us-east-1 --stack-name "$CERT_STACK" \
    >/dev/null 2>&1; then
    aws cloudformation create-stack --region us-east-1 --stack-name "$CERT_STACK" \
      --template-body file://deploy/aws/cert.yaml \
      --parameters "ParameterKey=DomainName,ParameterValue=$DOMAIN" \
      --tags Key=Project,Value=quiet-camps --query StackId --output text
  fi
  local arn="" record=""
  for _ in $(seq 1 30); do
    arn=$(aws cloudformation describe-stack-resources --region us-east-1 \
      --stack-name "$CERT_STACK" --output text \
      --query "StackResources[?LogicalResourceId=='Certificate'].PhysicalResourceId")
    if [[ "$arn" == arn:* ]]; then
      record=$(aws acm describe-certificate --region us-east-1 --certificate-arn "$arn" --query \
        "Certificate.DomainValidationOptions[0].ResourceRecord.[Name, Value]" --output text)
      [[ -n "$record" && "$record" != None* ]] && break
    fi
    sleep 5
  done
  echo "Add this CNAME at the DNS host for $DOMAIN (name, then value):"
  echo "  $record"
  echo "Waiting for ACM to see it..."
  aws cloudformation wait stack-create-complete --region us-east-1 --stack-name "$CERT_STACK"
  echo "Validated. Now: ship.sh deploy"
}

deploy() {
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Commit first: the image is tagged with the commit it was built from." >&2
    exit 1
  fi
  local repo image
  repo=$(output "$ECR_STACK" RepositoryUri)
  image="$repo:$(git rev-parse --short=12 HEAD)"

  echo "== The API image: $image"
  aws ecr get-login-password | docker login --username AWS --password-stdin "${repo%%/*}"
  # One arm64 image, no attestations: Lambda takes a single-platform image manifest.
  if aws ecr describe-images --repository-name quiet-camps-api \
    --image-ids imageTag="${image##*:}" >/dev/null 2>&1; then
    echo "already pushed"
  else
    docker buildx build --platform linux/arm64 --provenance=false --sbom=false \
      --tag "$image" --push api
  fi

  echo "== The stack"
  aws cloudformation deploy --stack-name "$STACK" --template-file deploy/aws/template.yaml \
    --capabilities CAPABILITY_IAM --tags "${TAGS[@]}" --no-fail-on-empty-changeset \
    --parameter-overrides "ImageUri=$image" \
    "DatabaseUrl=${NEON_DATABASE_URL/#postgresql:/postgresql+psycopg:}" \
    "OriginSecret=$ORIGIN_SECRET" "DomainName=$DOMAIN" "CertificateArn=$(certificate)"

  echo "== The web"
  (cd web && pnpm install --frozen-lockfile && pnpm build)
  local bucket
  bucket=$(output "$STACK" BucketName)
  # Vite's assets/ have a content hash in each name, so they never change: cache for a year.
  # The rest (index.html, the favicon, sounds) keep their names: browsers check back.
  aws s3 sync web/dist/assets "s3://$bucket/assets" \
    --cache-control "public, max-age=31536000, immutable"
  aws s3 sync web/dist "s3://$bucket" --exclude "assets/*" --exclude index.html \
    --cache-control "public, max-age=3600"
  aws s3 cp web/dist/index.html "s3://$bucket/index.html" --cache-control "no-cache"
  aws cloudfront create-invalidation --distribution-id "$(output "$STACK" DistributionId)" \
    --paths "/*" --query Invalidation.Id --output text

  echo "== Live at $(output "$STACK" SiteUrl)"
}

status() {
  aws cloudformation describe-stacks --query \
    "Stacks[?starts_with(StackName, 'quiet-camps')].[StackName, StackStatus, LastUpdatedTime]" \
    --output table
  local site
  site=$(output "$STACK" SiteUrl)
  echo "$site/api/health: $(curl -s -m 30 "$site/api/health")"
  # Cost Explorer bills US$0.01 per request.
  aws ce get-cost-and-usage --region us-east-1 --granularity MONTHLY --metrics UnblendedCost \
    --time-period "Start=$(date +%Y-%m-01),End=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d tomorrow +%F)" \
    --query "ResultsByTime[0].Total.UnblendedCost.[Amount, Unit]" --output text |
    xargs printf "This month so far (the whole account): %s %s\n"
}

teardown() {
  read -r -p "Delete the site, the API and the image repository? Type yes: " answer
  [[ "$answer" == yes ]] || exit 1
  local bucket
  bucket=$(output "$STACK" BucketName)
  aws s3 rm "s3://$bucket" --recursive # CloudFormation can't delete a bucket with files in it
  aws cloudformation delete-stack --stack-name "$STACK"
  aws cloudformation wait stack-delete-complete --stack-name "$STACK"
  aws cloudformation delete-stack --stack-name "$ECR_STACK"
  aws cloudformation wait stack-delete-complete --stack-name "$ECR_STACK"
  # After the distribution: a certificate in use can't be deleted.
  aws cloudformation delete-stack --region us-east-1 --stack-name "$CERT_STACK"
  aws cloudformation wait stack-delete-complete --region us-east-1 --stack-name "$CERT_STACK"
  echo "Deleted. The Neon database is separate: delete it in Neon's console."
}

case "${1:-}" in
  bootstrap | cert | deploy | status | teardown) "$1" ;;
  *)
    echo "usage: $0 bootstrap|cert|deploy|status|teardown" >&2
    exit 2
    ;;
esac
