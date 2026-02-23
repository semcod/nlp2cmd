#!/usr/bin/env bash
code2logic ./src -f toon --compact --function-logic --with-schema -o project.toon
rm project.toon