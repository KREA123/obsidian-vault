// BLE transport for the Claude desktop "Hardware Buddy" protocol:
// Nordic UART Service, LE Secure Connections with a 6-digit passkey shown
// on our screen. Adapted from anthropics/claude-desktop-buddy (MIT,
// Copyright 2026 Anthropic, PBC).
#pragma once
#include <stddef.h>
#include <stdint.h>

void bleInit(const char* deviceName);
bool bleConnected();
bool bleSecure();
uint32_t blePasskey();  // non-zero while pairing: show it on screen
void bleClearBonds();
size_t bleAvailable();
int bleRead();
size_t bleWrite(const uint8_t* data, size_t len);
