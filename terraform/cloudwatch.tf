##############################################################################
# CloudWatch — Backup Freshness Alarm
#
# The backup script (scripts/backup-db.sh) emits a custom CloudWatch metric
# after each run:
#
#   Namespace : Caregist/Backup
#   MetricName: BackupSuccess
#   Dimensions: [{ Name: "Environment", Value: "${environment}" }]
#   Value     : 1 (success) or 0 (failure)
#
# This alarm fires if the metric is missing for more than 30 hours — meaning
# no backup attempt landed (script not running) or the metric emission itself
# failed. The alarm also fires if the backup script explicitly reports 0.
#
# Alert destination: configure the SNS topic ARN below.
# TODO(owner): Create an SNS topic (or reuse an existing ops topic) and set
# BACKUP_ALERT_SNS_ARN in your tfvars. Then uncomment the aws_sns_topic_*
# resources below or point the alarm at your existing topic.
##############################################################################

# TODO(owner): Uncomment and configure one of these SNS options:
#
# Option A — create a new topic and subscribe ops@caregist.co.uk:
#
# resource "aws_sns_topic" "backup_alerts" {
#   name = "${var.project_name}-backup-alerts-${var.environment}"
# }
#
# resource "aws_sns_topic_subscription" "backup_alerts_email" {
#   topic_arn = aws_sns_topic.backup_alerts.arn
#   protocol  = "email"
#   endpoint  = "ops@caregist.co.uk"
# }
#
# Option B — reference an existing topic:
#
# data "aws_sns_topic" "ops_alerts" {
#   name = "your-existing-ops-topic"
# }

resource "aws_cloudwatch_metric_alarm" "backup_missing" {
  alarm_name          = "${var.project_name}-backup-missing-${var.environment}"
  alarm_description   = "No Caregist DB backup has landed in the last 30 hours. Check cron and backup script logs on EC2."
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  threshold           = 1
  treat_missing_data  = "breaching"

  # Use the metric emitted by scripts/backup-db.sh.
  namespace   = "Caregist/Backup"
  metric_name = "BackupSuccess"
  dimensions = {
    Environment = var.environment
  }

  # 30 hours = 108000 seconds. If no data point arrives in this window,
  # treat_missing_data = "breaching" fires the alarm.
  period    = 108000
  statistic = "Maximum"

  # TODO(owner): Set alarm_actions to your SNS topic ARN once created.
  # alarm_actions = [aws_sns_topic.backup_alerts.arn]
  # ok_actions    = [aws_sns_topic.backup_alerts.arn]

  tags = {
    Name = "${var.project_name}-backup-missing-${var.environment}"
  }
}
