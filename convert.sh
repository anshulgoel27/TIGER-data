#!/bin/bash

INPATH=$1
OUTPATH=$2

if [[ ! -d "$INPATH" ]]; then
    echo "Input path does not exist"
    exit 1
fi

if [[ ! -d "$OUTPATH" ]]; then
    echo "Output path does not exist"
    exit 1
fi

INREGEX='_([0-9]{5})_edges.zip'
WORKPATH="$OUTPATH/tmp-workdir/"
mkdir -p "$WORKPATH"

INFILES=($INPATH/*.zip)
echo "Found ${#INFILES[*]} files."

# Determine the number of CPUs available
NUMCPU=$(nproc)
echo "Using $NUMCPU parallel processes."

process_file() {
    local F=$1
    local INREGEX='_([0-9]{5})_edges.zip'
    local WORKPATH="$OUTPATH/tmp-workdir/"
    local OUTPATH="$2"

    if [[ "$F" =~ $INREGEX ]]; then
        local COUNTYID=${BASH_REMATCH[1]}
        local SHAPEFILE="$WORKPATH/$(basename "$F" '.zip').shp"
        local CSVFILE="$OUTPATH/$COUNTYID.csv"

        unzip -o -q -d "$WORKPATH" "$F"
        if [[ ! -e "$SHAPEFILE" ]]; then
            echo "Unzip failed. $SHAPEFILE not found."
            exit 1
        fi

        ./tiger_address_convert.py "$SHAPEFILE" "$CSVFILE"
        rm "$WORKPATH"/*
    fi
}

export -f process_file
export OUTPATH

# Use `parallel` with dynamic CPU count
printf "%s\n" "${INFILES[@]}" | parallel -j "$NUMCPU" process_file {} "$OUTPATH"

OUTFILES=($OUTPATH/*.csv)
echo "Wrote ${#OUTFILES[*]} files."

rmdir "$WORKPATH"
