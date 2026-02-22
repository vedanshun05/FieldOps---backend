#!/bin/bash
# ─────────────────────────────────────────────────────────────
# FieldOps AI — Manual API Testing Script
# Tests all API endpoints via curl against http://localhost:8000
#
# Usage:  chmod +x test_api.sh && ./test_api.sh
# ─────────────────────────────────────────────────────────────

BASE="http://localhost:8000"
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

pass=0
fail=0

test_endpoint() {
    local method="$1"
    local path="$2"
    local label="$3"
    local data="$4"

    echo -e "\n${CYAN}─────────────────────────────────────────${NC}"
    echo -e "${BOLD}${label}${NC}"
    echo -e "${YELLOW}${method} ${path}${NC}"

    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "${BASE}${path}")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "${BASE}${path}" \
            -H "Content-Type: application/json" -d "$data")
    fi

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == 2* ]]; then
        echo -e "${GREEN}✅ HTTP ${http_code}${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        ((pass++))
    else
        echo -e "${RED}❌ HTTP ${http_code}${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        ((fail++))
    fi
}

echo -e "${BOLD}"
echo "══════════════════════════════════════════════════"
echo "   🚀 FIELDOPS AI — MANUAL API TEST SUITE"
echo "══════════════════════════════════════════════════"
echo -e "${NC}"

# ─── 1. Health Check ─────────────────────────────────────────
test_endpoint "GET" "/api/health" "1. Health Check"

# ─── 2. Root Endpoint ────────────────────────────────────────
test_endpoint "GET" "/" "2. Root Endpoint"

# ─── 3. Dashboard Summary ───────────────────────────────────
test_endpoint "GET" "/api/dashboard/summary" "3. Dashboard Summary"

# ─── 4. Jobs List ────────────────────────────────────────────
test_endpoint "GET" "/api/dashboard/jobs" "4. Jobs List"

# ─── 5. Inventory ────────────────────────────────────────────
test_endpoint "GET" "/api/dashboard/inventory" "5. Inventory"

# ─── 6. Follow-ups ──────────────────────────────────────────
test_endpoint "GET" "/api/dashboard/followups" "6. Follow-ups"

# ─── 7. Alerts ───────────────────────────────────────────────
test_endpoint "GET" "/api/dashboard/alerts" "7. Alerts (Retention Layer)"

# ─── 8. Voice Processing (requires audio file) ──────────────
echo -e "\n${CYAN}─────────────────────────────────────────${NC}"
echo -e "${BOLD}8. Voice Processing (POST /api/voice)${NC}"
echo -e "${YELLOW}POST /api/voice${NC}"

# Create a tiny test WAV file (silence)
python3 -c "
import struct, wave
f = wave.open('/tmp/test_voice.wav', 'w')
f.setnchannels(1)
f.setsampwidth(2)
f.setframerate(16000)
f.writeframes(struct.pack('<' + 'h' * 16000, *([0] * 16000)))
f.close()
print('Created test WAV file')
" 2>/dev/null

if [ -f /tmp/test_voice.wav ]; then
    response=$(curl -s -w "\n%{http_code}" -X POST "${BASE}/api/voice" \
        -F "file=@/tmp/test_voice.wav;type=audio/wav")
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == 2* ]]; then
        echo -e "${GREEN}✅ HTTP ${http_code}${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null | head -30
        echo "  ... (truncated)"
        ((pass++))
    else
        echo -e "${RED}❌ HTTP ${http_code} (Expected — needs Ollama + Whisper running)${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
        ((fail++))
    fi
    rm -f /tmp/test_voice.wav
else
    echo -e "${YELLOW}⚠️  Skipped (couldn't create test audio file)${NC}"
fi

# ─── 9. API Docs ─────────────────────────────────────────────
test_endpoint "GET" "/docs" "9. Swagger Docs (HTML page)"

# ─── Summary ─────────────────────────────────────────────────
echo -e "\n${BOLD}"
echo "══════════════════════════════════════════════════"
echo -e "   📊 Results: ${GREEN}${pass} passed${NC}${BOLD}, ${RED}${fail} failed${NC}"
echo "══════════════════════════════════════════════════"
echo -e "${NC}"
