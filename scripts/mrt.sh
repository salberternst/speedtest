#!/bin/bash

TARGET="8.8.8.8"
LOGFILE="mtr_excel_log.csv"

usage() {
    cat <<EOF
Usage: $0 [--target HOST] [--logfile PATH]

Options:
  --target HOST    MTR target host or IP (default: $TARGET)
  --logfile PATH   CSV output file (default: $LOGFILE)
  -h, --help       Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            if [[ -z "$2" ]]; then
                echo "Missing value for --target" >&2
                usage
                exit 1
            fi
            TARGET="$2"
            shift 2
            ;;
        --logfile)
            if [[ -z "$2" ]]; then
                echo "Missing value for --logfile" >&2
                usage
                exit 1
            fi
            LOGFILE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [ ! -f "$LOGFILE" ]; then
    echo "Timestamp,Hop,IP,Loss(%),Snt,Drop,Last,Best,Avg,Wrst,StDev" > "$LOGFILE"
fi

while true; do
    TIMESTAMP=$(date +'%Y-%m-%d %H:%M:%S')

    mtr -r -n -c 10 --csv "$TARGET" | tail -n +2 | awk -v ts="$TIMESTAMP" -F',' '{OFS=","; print ts, $5, $6, $7, $8, $9, $11, $12, $13, $14, $15}' >> "$LOGFILE"
done
