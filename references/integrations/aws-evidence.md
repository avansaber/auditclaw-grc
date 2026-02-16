# AWS Evidence Collection Guide

**Purpose:** Collect compliance evidence from AWS services for SOC 2, ISO 27001, HIPAA, NIST CSF, PCI DSS, and other frameworks.

## Quick Start

```bash
# Store evidence from any AWS CLI command
aws s3api get-bucket-encryption --bucket my-bucket \
  | python3 scripts/db_query.py --action add-evidence \
    --title "S3 Encryption - my-bucket" --type automated \
    --source aws-cli --control-ids 12,45 \
    --valid-from 2026-01-01 --valid-until 2026-04-01
```

Save output to a file first, then record in the DB:
```bash
aws s3api get-bucket-encryption --bucket my-bucket > /tmp/s3-encryption.json
python3 scripts/db_query.py --action add-evidence \
  --title "S3 Encryption - my-bucket" --type automated \
  --source aws-cli --filepath /tmp/s3-encryption.json \
  --control-ids 12,45 --valid-from 2026-01-01 --valid-until 2026-04-01
```

## Evidence by Control Domain

### 1. Access Control (IAM)

**Controls:** SOC 2 CC6.1–CC6.3, ISO 27001 A.9.x, NIST PR.AC, HIPAA §164.312(a), CIS 5.x/6.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| IAM credential report | `aws iam generate-credential-report && aws iam get-credential-report --output text --query Content \| base64 -d` | Monthly |
| MFA status for all users | `aws iam list-users --query 'Users[*].UserName' \| xargs -I{} aws iam list-mfa-devices --user-name {}` | Monthly |
| Password policy | `aws iam get-account-password-policy` | Quarterly |
| Service control policies | `aws organizations list-policies --filter SERVICE_CONTROL_POLICY` | Quarterly |
| Access analyzer findings | `aws accessanalyzer list-findings --analyzer-arn <arn>` | Weekly |
| Unused credentials (>90 days) | `aws iam get-credential-report`, parse `password_last_used` and `access_key_*_last_used` | Monthly |
| Root account usage | `aws iam get-credential-report`, check root row `password_last_used` | Monthly |

**Key checks:**
- Root account has MFA enabled and no access keys
- All human users have MFA enabled
- No credentials unused > 90 days
- Password policy meets requirements (14+ chars, complexity, 90-day rotation)

### 2. Encryption (Data Protection)

**Controls:** SOC 2 CC6.1/CC6.7, ISO 27001 A.10.x, NIST PR.DS-1/PR.DS-2, HIPAA §164.312(a)(2)(iv), PCI DSS 3.4

| Evidence | Command | Refresh |
|----------|---------|---------|
| S3 bucket encryption | `aws s3api get-bucket-encryption --bucket <name>` | Quarterly |
| S3 public access block | `aws s3api get-public-access-block --bucket <name>` | Monthly |
| EBS default encryption | `aws ec2 get-ebs-encryption-by-default` | Quarterly |
| RDS encryption status | `aws rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier,StorageEncrypted,KmsKeyId]'` | Quarterly |
| KMS key rotation | `aws kms get-key-rotation-status --key-id <id>` | Quarterly |
| ELB/ALB SSL policy | `aws elbv2 describe-listeners --load-balancer-arn <arn> --query 'Listeners[*].[Protocol,SslPolicy]'` | Quarterly |
| CloudFront HTTPS config | `aws cloudfront get-distribution --id <id> --query 'Distribution.DistributionConfig.ViewerCertificate'` | Quarterly |

**Key checks:**
- All S3 buckets have default encryption (AES-256 or aws:kms)
- All S3 buckets have public access block enabled
- EBS encryption by default is enabled in all regions
- RDS instances use encryption at rest
- KMS keys have automatic rotation enabled
- Load balancers enforce TLS 1.2+

### 3. Logging and Monitoring

**Controls:** SOC 2 CC7.2/CC7.3, ISO 27001 A.12.4.x, NIST DE.CM/DE.AE, HIPAA §164.312(b), CIS 8.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| CloudTrail status | `aws cloudtrail describe-trails && aws cloudtrail get-trail-status --name <trail>` | Monthly |
| CloudTrail log validation | `aws cloudtrail get-trail --name <trail> --query 'Trail.[LogFileValidationEnabled,IsMultiRegionTrail,KMSKeyId]'` | Quarterly |
| CloudWatch alarms | `aws cloudwatch describe-alarms --state-value OK --query 'MetricAlarms[*].[AlarmName,MetricName,Namespace]'` | Monthly |
| GuardDuty status | `aws guardduty list-detectors && aws guardduty get-detector --detector-id <id>` | Monthly |
| VPC flow logs | `aws ec2 describe-flow-logs --query 'FlowLogs[*].[FlowLogId,ResourceId,LogGroupName,TrafficType]'` | Quarterly |
| Config recorder status | `aws configservice describe-configuration-recorder-status` | Monthly |
| S3 access logging | `aws s3api get-bucket-logging --bucket <name>` | Quarterly |

**Key checks:**
- CloudTrail enabled in all regions with log file validation
- CloudTrail logs encrypted with KMS
- GuardDuty enabled in all regions
- VPC flow logs enabled for all VPCs
- AWS Config recording enabled
- CloudWatch alarms for unauthorized API calls, root usage, console sign-in failures

### 4. Network Security

**Controls:** SOC 2 CC6.6, ISO 27001 A.13.x, NIST PR.AC-5, PCI DSS 1.x, CIS 12.x/13.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| Security group rules | `aws ec2 describe-security-groups --query 'SecurityGroups[*].[GroupId,GroupName,IpPermissions]'` | Monthly |
| Open 0.0.0.0/0 ingress | `aws ec2 describe-security-groups --filters Name=ip-permission.cidr,Values=0.0.0.0/0` | Weekly |
| NACLs | `aws ec2 describe-network-acls` | Quarterly |
| VPC peering connections | `aws ec2 describe-vpc-peering-connections` | Quarterly |
| WAF rules | `aws wafv2 list-web-acls --scope REGIONAL` | Quarterly |
| Public subnets | `aws ec2 describe-route-tables --query 'RouteTables[*].Routes[?GatewayId!=null && starts_with(GatewayId, \`igw-\`)]'` | Quarterly |

**Key checks:**
- No security groups allow 0.0.0.0/0 ingress to SSH (22) or RDP (3389)
- No security groups allow 0.0.0.0/0 ingress to database ports (3306, 5432, 1433)
- WAF is deployed in front of public-facing applications
- VPC architecture uses public/private subnet segregation

### 5. Backup and Recovery

**Controls:** SOC 2 A1.2, ISO 27001 A.12.3, NIST PR.IP-4, HIPAA §164.308(a)(7), CIS 11.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| AWS Backup plans | `aws backup list-backup-plans` | Quarterly |
| Backup vault contents | `aws backup list-recovery-points-by-backup-vault --backup-vault-name <name>` | Monthly |
| RDS automated backups | `aws rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier,BackupRetentionPeriod]'` | Quarterly |
| S3 versioning | `aws s3api get-bucket-versioning --bucket <name>` | Quarterly |
| DynamoDB PITR | `aws dynamodb describe-continuous-backups --table-name <name>` | Quarterly |

### 6. Incident Response

**Controls:** SOC 2 CC7.4/CC7.5, ISO 27001 A.16.x, NIST RS.x, HIPAA §164.308(a)(6)

| Evidence | Command | Refresh |
|----------|---------|---------|
| GuardDuty findings | `aws guardduty list-findings --detector-id <id> --finding-criteria '{"Criterion":{"severity":{"Gte":7}}}'` | Weekly |
| Security Hub findings | `aws securityhub get-findings --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}'` | Weekly |
| Inspector findings | `aws inspector2 list-findings --filter-criteria '{"severity":[{"comparison":"EQUALS","value":"CRITICAL"}]}'` | Weekly |
| EventBridge rules | `aws events list-rules --name-prefix security` | Quarterly |

### 7. Vulnerability Management

**Controls:** SOC 2 CC7.1, ISO 27001 A.12.6, NIST DE.CM-8, PCI DSS 6.x/11.x, CIS 7.x/16.x

| Evidence | Command | Refresh |
|----------|---------|---------|
| Inspector scan coverage | `aws inspector2 list-coverage --filter-criteria '{"resourceType":[{"comparison":"EQUALS","value":"AWS_EC2_INSTANCE"}]}'` | Monthly |
| ECR image scan findings | `aws ecr describe-image-scan-findings --repository-name <name> --image-id imageTag=latest` | Per build |
| SSM patch compliance | `aws ssm describe-instance-patch-states --instance-ids <ids>` | Weekly |
| Outdated AMIs | `aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,ImageId,LaunchTime]'` | Monthly |

## Automation Tips

### Bulk Collection Script
```bash
#!/bin/bash
# Collect all evidence for quarterly audit
DATE=$(date +%Y-%m-%d)
OUT=~/.openclaw/grc/evidence/automated/aws-$DATE

mkdir -p $OUT
aws iam generate-credential-report > /dev/null 2>&1; sleep 5
aws iam get-credential-report --output text --query Content | base64 -d > $OUT/iam-credential-report.csv
aws ec2 describe-security-groups > $OUT/security-groups.json
aws s3api list-buckets --query 'Buckets[*].Name' --output text | tr '\t' '\n' | while read b; do
  aws s3api get-bucket-encryption --bucket "$b" 2>/dev/null > "$OUT/s3-encryption-$b.json"
done
aws cloudtrail describe-trails > $OUT/cloudtrail.json
aws configservice describe-configuration-recorder-status > $OUT/config-status.json
echo "Evidence collected to $OUT"
```

### Suggested Refresh Schedule

| Frequency | Evidence Types |
|-----------|---------------|
| Weekly | GuardDuty findings, open security groups, patch compliance |
| Monthly | IAM credential report, MFA status, CloudWatch alarms |
| Quarterly | Encryption configs, backup plans, network architecture, KMS rotation |
| Per change | Security group modifications, IAM policy changes |

### Evidence Validity

Set `--valid-until` based on evidence type:
- **Configuration snapshots** (encryption, IAM policy): 90 days
- **Scan results** (vulnerability, compliance): 30 days
- **Audit reports** (credential report): 90 days
- **Architecture docs** (network diagrams): 180 days
