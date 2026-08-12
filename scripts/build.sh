#!/usr/bin/env bash
# HermesDashboard 空壳应用打包脚本
#
# 用法（在 NAS 构建目录运行）:
#   bash scripts/build.sh            # 版本号自动累加第4位
#   bash scripts/build.sh --formal   # 正式版：升第3位
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CUR_VER="$(cat "$ROOT/VERSION" 2>/dev/null | tr -d '[:space:]')"
[ -z "$CUR_VER" ] && CUR_VER="1.0.0"
FPK_DIR="/vol1/1000/fnOS App/fpk/HermesDashboard"
OLDFPK_DIR="/vol1/1000/fnOS App/fpk/oldfpk"

MODE="${1:-}"
if [ "$MODE" = "--formal" ]; then
    IFS='.' read -ra P <<< "$CUR_VER"
    VER="${P[0]}.${P[1]}.$(( ${P[2]:-0} + 1 ))"
else
    if [[ "$CUR_VER" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
        VER="${BASH_REMATCH[1]}.${BASH_REMATCH[2]}.${BASH_REMATCH[3]}.$((BASH_REMATCH[4] + 1))"
    else
        VER="${CUR_VER}.1"
    fi
fi
echo "ℹ️  打包版本：$CUR_VER -> $VER"

sed -i "s/^version.*/version               = $VER/" "$ROOT/manifest"
echo "$VER" > "$ROOT/VERSION"

(cd "$ROOT" && fnpack build >/dev/null 2>&1)
mv "$ROOT/HermesDashboard.fpk" "$ROOT/HermesDashboard-$VER.fpk"
echo "✓ 构建完成：HermesDashboard-$VER.fpk"

mkdir -p "$OLDFPK_DIR"
mkdir -p "$FPK_DIR"
mv "$FPK_DIR"/HermesDashboard-*.fpk "$OLDFPK_DIR"/ 2>/dev/null || true
cp "$ROOT/HermesDashboard-$VER.fpk" "$FPK_DIR/"
rm -f "$ROOT/HermesDashboard-$VER.fpk"
echo "✓ 已交付：$FPK_DIR/HermesDashboard-$VER.fpk"
