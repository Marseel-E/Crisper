#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ -z "$1" ]; then
    echo -e "${RED}Error: No input video provided.${NC}"
    echo -e "Usage: ./test_suite.sh <input_video.mp4> [target_height]"
    exit 1
fi

INPUT_VID="$1"
TARGET_HEIGHT="${2:-1080}"

TIMESTAMP=$(date +"%H-%M-%S")
OUT_DIR="test_results_${TIMESTAMP}"
mkdir -p "$OUT_DIR"

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}✨ CRISPER BRUTE TEST SUITE INITIALIZED ✨${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "Input File: ${YELLOW}$INPUT_VID${NC}"
echo -e "Target Height: ${YELLOW}${TARGET_HEIGHT}p${NC}"
echo -e "Output Directory: ${YELLOW}$OUT_DIR${NC}\n"

run_test() {
    local test_name="$1"
    shift
    local cmd=("$@")

    echo -e "${CYAN}▶ Running:${NC} $test_name"
    
    if "${cmd[@]}"; then
        echo -e "${GREEN}✅ Passed:${NC} $test_name\n"
    else
        echo -e "${RED}❌ Failed:${NC} $test_name\n"
    fi
}

echo -e "${YELLOW}--- Phase 1: Math Plugins ---${NC}"
for plugin in "LanczosUpscaler" "LetterboxPadder"; do
    out_file="${OUT_DIR}/Math_${plugin}.mp4"
    run_test "$plugin" python3 . "$INPUT_VID" "$out_file" --headless --plugin "$plugin" --height "$TARGET_HEIGHT"
done

echo -e "${YELLOW}--- Phase 2: NCNN Engines ---${NC}"
for plugin in "NCNN_X4Plus" "NCNN_Anime"; do
    out_file="${OUT_DIR}/NCNN_${plugin}.mp4"
    run_test "$plugin" python3 . "$INPUT_VID" "$out_file" --headless --plugin "$plugin" --height "$TARGET_HEIGHT"
done

echo -e "${YELLOW}--- Phase 3: PyTorch MPS Engine ---${NC}"

MODELS=$(find ./models -type f \( -name "*.pth" -o -name "*.safetensors" \))

if [ -z "$MODELS" ]; then
    echo -e "${RED}No PyTorch models found in ./models/. Skipping Phase 3.${NC}\n"
else
    for model in $MODELS; do
        model_name=$(basename "$model")
        clean_name="${model_name%.*}"
        out_file="${OUT_DIR}/PyTorch_${clean_name}.mp4"
        
        tiling_flag=""
        if [[ "$clean_name" == *"Nomos"* ]]; then
            tiling_flag="--tiling"
            test_desc="PyTorch_MPS_Engine ($clean_name) [TILED]"
        else
            test_desc="PyTorch_MPS_Engine ($clean_name)"
        fi

        if [ -n "$tiling_flag" ]; then
            run_test "$test_desc" python3 . "$INPUT_VID" "$out_file" --headless --plugin "PyTorch_MPS_Engine" --height "$TARGET_HEIGHT" --model_path "$model" --tiling
        else
            run_test "$test_desc" python3 . "$INPUT_VID" "$out_file" --headless --plugin "PyTorch_MPS_Engine" --height "$TARGET_HEIGHT" --model_path "$model"
        fi
    done
fi

echo -e "${YELLOW}--- Phase 4: Swarm Protocol ---${NC}"

out_file="${OUT_DIR}/Swarm_NCNN_Anime.mp4"
run_test "Swarm 2-Node (NCNN_Anime)" python3 . "$INPUT_VID" "$out_file" --headless --plugin "NCNN_Anime" --height "$TARGET_HEIGHT" --swarm 2

echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}🎉 BRUTE TEST SUITE COMPLETE 🎉${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "Check the ${YELLOW}$OUT_DIR${NC} folder for all output files to review visual quality."