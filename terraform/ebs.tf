##############################################################################
# EBS Encryption — Default CMK Configuration
#
# IMPORTANT: AWS EBS volumes CANNOT be encrypted in-place.
# The existing volume holding BLOB_STORAGE_PATH must be migrated manually
# using a snapshot → copy-with-encryption → swap procedure. This Terraform
# resource sets the account-level default KMS key so that any NEW volumes
# created in this account/region will automatically use the CMK.
#
# ── Manual Migration Procedure for the Existing EBS Volume ──────────────────
#
# Prerequisites:
#   - aws CLI configured with an admin role
#   - VOLUME_ID: the EBS volume currently holding BLOB_STORAGE_PATH
#   - KMS_KEY_ARN: output from `terraform output kms_key_arn`
#   - INSTANCE_ID: the EC2 instance ID
#   - DEVICE_NAME: the device path (e.g. /dev/xvdb) — check `lsblk` on the instance
#
# Step 1 — Create a snapshot of the existing (unencrypted) volume:
#
#   SNAP_ID=$(aws ec2 create-snapshot \
#     --region eu-west-2 \
#     --volume-id "${VOLUME_ID}" \
#     --description "Pre-encryption snapshot of BLOB_STORAGE_PATH volume" \
#     --query SnapshotId --output text)
#   echo "Snapshot: ${SNAP_ID}"
#
#   # Wait until the snapshot is complete (may take several minutes):
#   aws ec2 wait snapshot-completed --region eu-west-2 --snapshot-ids "${SNAP_ID}"
#
# Step 2 — Copy the snapshot with encryption enabled:
#
#   ENC_SNAP_ID=$(aws ec2 copy-snapshot \
#     --region eu-west-2 \
#     --source-region eu-west-2 \
#     --source-snapshot-id "${SNAP_ID}" \
#     --encrypted \
#     --kms-key-id "${KMS_KEY_ARN}" \
#     --description "Encrypted copy for BLOB_STORAGE_PATH migration" \
#     --query SnapshotId --output text)
#   echo "Encrypted snapshot: ${ENC_SNAP_ID}"
#
#   aws ec2 wait snapshot-completed --region eu-west-2 --snapshot-ids "${ENC_SNAP_ID}"
#
# Step 3 — Create a new encrypted volume from the encrypted snapshot:
#
#   # Get the AZ of the existing volume first:
#   AZ=$(aws ec2 describe-volumes --region eu-west-2 \
#     --volume-ids "${VOLUME_ID}" \
#     --query 'Volumes[0].AvailabilityZone' --output text)
#
#   NEW_VOL_ID=$(aws ec2 create-volume \
#     --region eu-west-2 \
#     --snapshot-id "${ENC_SNAP_ID}" \
#     --availability-zone "${AZ}" \
#     --volume-type gp3 \
#     --encrypted \
#     --kms-key-id "${KMS_KEY_ARN}" \
#     --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=caregist-blob-storage-encrypted}]' \
#     --query VolumeId --output text)
#   echo "New encrypted volume: ${NEW_VOL_ID}"
#
#   aws ec2 wait volume-available --region eu-west-2 --volume-ids "${NEW_VOL_ID}"
#
# Step 4 — Stop the EC2 instance (coordinate downtime window):
#
#   aws ec2 stop-instances --region eu-west-2 --instance-ids "${INSTANCE_ID}"
#   aws ec2 wait instance-stopped --region eu-west-2 --instance-ids "${INSTANCE_ID}"
#
# Step 5 — Detach the old volume and attach the new encrypted one:
#
#   aws ec2 detach-volume --region eu-west-2 --volume-id "${VOLUME_ID}"
#   aws ec2 wait volume-available --region eu-west-2 --volume-ids "${VOLUME_ID}"
#
#   aws ec2 attach-volume \
#     --region eu-west-2 \
#     --volume-id "${NEW_VOL_ID}" \
#     --instance-id "${INSTANCE_ID}" \
#     --device "${DEVICE_NAME}"
#   aws ec2 wait volume-in-use --region eu-west-2 --volume-ids "${NEW_VOL_ID}"
#
# Step 6 — Start the instance and verify BLOB_STORAGE_PATH is accessible:
#
#   aws ec2 start-instances --region eu-west-2 --instance-ids "${INSTANCE_ID}"
#   aws ec2 wait instance-running --region eu-west-2 --instance-ids "${INSTANCE_ID}"
#   # SSH in and confirm: ls -la ${BLOB_STORAGE_PATH}
#
# Step 7 — Delete the old unencrypted volume (irreversible — verify data first!):
#
#   aws ec2 delete-volume --region eu-west-2 --volume-id "${VOLUME_ID}"
#
# ── End of Manual Migration Procedure ───────────────────────────────────────
##############################################################################

# Set the account-level default KMS key for EBS in eu-west-2.
# Any NEW EBS volume created in this account/region (by any mechanism:
# launch template, ASG, EC2 console) will be encrypted with this CMK.
resource "aws_ebs_default_kms_key" "this" {
  key_arn = aws_kms_key.backup.arn
}
