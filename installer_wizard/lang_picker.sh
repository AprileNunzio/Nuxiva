#!/usr/bin/env bash

LP_CHOICES=(
    "en|English" "it|Italiano" "fr|Français" "es|Español"
)
LP_IDLE_LIMIT=${LP_IDLE_LIMIT:-120}
LP_STEP=${LP_STEP:-14}
LP_STTY=""
LP_MICE_PID=""
LP_MFD=""
PICKED_LANG=""

lp_valid_code() {
    local c
    for c in "${LP_CHOICES[@]}"; do
        [ "${c%%|*}" = "$1" ] && return 0
    done
    return 1
}

lp_detect() {
    local l="${NUXIVA_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-en}}}}"
    l="${l,,}"
    l="${l%%.*}"
    l="${l%%_*}"
    lp_valid_code "$l" && { printf '%s\n' "$l"; return 0; }
    printf 'en\n'
}

lp_mouse_on() {
    [ -r /dev/input/mice ] || modprobe mousedev >/dev/null 2>&1 || true
    [ -r /dev/input/mice ] || return 0
    command -v stdbuf >/dev/null 2>&1 || return 0
    coproc LP_MICE { exec stdbuf -oL od -An -v -tu1 -w3 /dev/input/mice 2>/dev/null; }
    LP_MFD=${LP_MICE[0]}
}

lp_restore() {
    [ -n "$LP_MICE_PID" ] && kill "$LP_MICE_PID" >/dev/null 2>&1 || true
    LP_MICE_PID="" LP_MFD=""
    printf '\033[?1006l\033[?1000l\033[?25h\033[0m' >/dev/tty 2>/dev/null || true
    [ -n "$LP_STTY" ] && stty "$LP_STTY" </dev/tty >/dev/null 2>&1 || true
    LP_STTY=""
}

lp_draw() {
    local i idx mark
    printf '\033[H\033[2J' >/dev/tty
    printf '\n  \033[1;36mNUXIVA\033[0m\n  Language · Lingua · Langue · Sprache · Idioma\n\n' >/dev/tty
    for (( i = 0; i < LP_VIS; i++ )); do
        idx=$(( LP_TOP + i ))
        (( idx < LP_N )) || break
        if (( idx == LP_SEL )); then
            printf '  \033[7m %s  %s  \033[0m\n' "$LP_MARK" "${LP_LABELS[idx]}" >/dev/tty
        else
            printf '     %s\n' "${LP_LABELS[idx]}" >/dev/tty
        fi
    done
    printf '\n  \033[2m↑ ↓  Enter  ·  mouse: move + click  ·  %s/%s\033[0m\n' "$(( LP_SEL + 1 ))" "$LP_N" >/dev/tty
}

lp_move() {
    local to=$1
    (( to < 0 )) && to=0
    (( to >= LP_N )) && to=$(( LP_N - 1 ))
    (( to == LP_SEL )) && return 0
    LP_SEL=$to
    (( LP_SEL < LP_TOP )) && LP_TOP=$LP_SEL
    (( LP_SEL >= LP_TOP + LP_VIS )) && LP_TOP=$(( LP_SEL - LP_VIS + 1 ))
    LP_DIRTY=1
}

lp_read_sgr() {
    local buf="" ch term="" btn x y
    while IFS= read -rsn1 -t 0.05 ch </dev/tty; do
        if [[ "$ch" == M || "$ch" == m ]]; then term=$ch; break; fi
        buf+=$ch
    done
    IFS=';' read -r btn x y <<<"$buf"
    [[ "$btn" =~ ^[0-9]+$ && "$y" =~ ^[0-9]+$ ]] || return 0
    case "$btn" in
        64) lp_move $(( LP_SEL - 1 )) ;;
        65) lp_move $(( LP_SEL + 1 )) ;;
        0)
            if [ "$term" = M ]; then
                local row=$(( y - 5 ))
                if (( row >= 0 && row < LP_VIS && LP_TOP + row < LP_N )); then
                    LP_SEL=$(( LP_TOP + row ))
                    LP_DONE=1
                fi
            fi
            ;;
    esac
}

lp_drain_mouse() {
    local a b c dy left
    [ -n "$LP_MFD" ] || return 0
    while read -r -t 0.001 -u "$LP_MFD" a b c; do
        [[ "$a" =~ ^[0-9]+$ && "$c" =~ ^[0-9]+$ ]] || continue
        (( a & 8 )) || continue
        dy=$c
        (( a & 32 )) && dy=$(( c - 256 ))
        LP_ACC=$(( LP_ACC + dy ))
        if (( LP_ACC >= LP_STEP )); then LP_ACC=0; lp_move $(( LP_SEL - 1 )); fi
        if (( LP_ACC <= -LP_STEP )); then LP_ACC=0; lp_move $(( LP_SEL + 1 )); fi
        left=$(( a & 1 ))
        if (( left == 1 && LP_PREV == 0 )); then LP_DONE=1; fi
        LP_PREV=$left
        LP_LAST=$SECONDS
    done
}

lp_key() {
    local key=$1 c1 c2 c3
    case "$key" in
        "") LP_DONE=1 ;;
        $'\033')
            IFS= read -rsn1 -t 0.02 c1 </dev/tty || return 0
            [ "$c1" = "[" ] || return 0
            IFS= read -rsn1 -t 0.02 c2 </dev/tty || return 0
            case "$c2" in
                A) lp_move $(( LP_SEL - 1 )) ;;
                B) lp_move $(( LP_SEL + 1 )) ;;
                H) lp_move 0 ;;
                F) lp_move $(( LP_N - 1 )) ;;
                5) IFS= read -rsn1 -t 0.02 c3 </dev/tty || true; lp_move $(( LP_SEL - LP_VIS )) ;;
                6) IFS= read -rsn1 -t 0.02 c3 </dev/tty || true; lp_move $(( LP_SEL + LP_VIS )) ;;
                "<") lp_read_sgr ;;
            esac
            ;;
        k|K) lp_move $(( LP_SEL - 1 )) ;;
        j|J) lp_move $(( LP_SEL + 1 )) ;;
    esac
}

pick_language() {
    local default=${1:-en} i lines
    LP_N=${#LP_CHOICES[@]}
    LP_CODES=() LP_LABELS=()
    for i in "${LP_CHOICES[@]}"; do
        LP_CODES+=("${i%%|*}")
        LP_LABELS+=("${i#*|}")
    done
    LP_SEL=0 LP_TOP=0 LP_DONE=0 LP_DIRTY=1 LP_ACC=0 LP_PREV=0 LP_LAST=$SECONDS
    for i in "${!LP_CODES[@]}"; do
        [ "${LP_CODES[i]}" = "$default" ] && LP_SEL=$i
    done
    lines=$(tput lines 2>/dev/null || echo 24)
    [[ "$lines" =~ ^[0-9]+$ ]] || lines=24
    LP_VIS=$(( lines - 9 ))
    (( LP_VIS < 4 )) && LP_VIS=4
    (( LP_VIS > LP_N )) && LP_VIS=$LP_N
    (( LP_SEL >= LP_VIS )) && LP_TOP=$(( LP_SEL - LP_VIS + 1 ))
    LP_MARK=">"
    [ "$(locale charmap 2>/dev/null || true)" = UTF-8 ] && LP_MARK="›"

    LP_STTY=$(stty -g </dev/tty 2>/dev/null) || { PICKED_LANG=$default; return 0; }
    trap 'lp_restore; exit 130' INT TERM
    stty -echo -icanon </dev/tty >/dev/null 2>&1 || true
    printf '\033[?25l\033[?1000h\033[?1006h' >/dev/tty
    lp_mouse_on

    local key
    while (( LP_DONE == 0 )); do
        (( LP_DIRTY )) && { lp_draw; LP_DIRTY=0; }
        lp_drain_mouse
        (( LP_DONE )) && break
        if IFS= read -rsn1 -t 0.03 key </dev/tty; then
            LP_LAST=$SECONDS
            lp_key "$key"
        fi
        if (( SECONDS - LP_LAST >= LP_IDLE_LIMIT )); then
            LP_SEL=0
            for i in "${!LP_CODES[@]}"; do
                [ "${LP_CODES[i]}" = "$default" ] && LP_SEL=$i
            done
            LP_DONE=1
        fi
    done

    PICKED_LANG=${LP_CODES[LP_SEL]}
    lp_restore
    trap - INT TERM
    printf '\033[H\033[2J' >/dev/tty 2>/dev/null || true
}
