#!/usr/bin/env bash
pip install code2llm --upgrade
#code2logic ./ -f toon --compact --no-repeat-module --function-logic --with-schema --name project -o ./
code2llm ./ -f toon,evolution,code2logic -o ./project