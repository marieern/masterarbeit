#!/bin/zsh
echo "--- Suche nach verbleibenden 'base_footprint' Einträgen ---"
# -n zeigt die Zeilennummer, -H den Dateinamen
grep -rnH "base_footprint" src/

echo "\n--- Prüfung der kompilierten Dateien (install-Ordner) ---"
if [ -d "install" ]; then
    grep -rn "base_footprint" install/ | head -n 10
fi
