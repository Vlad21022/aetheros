# Pull in every AetherOS package (package/<name>/<name>.mk).
include $(sort $(wildcard $(BR2_EXTERNAL_AETHEROS_PATH)/package/*/*.mk))
