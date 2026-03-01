#!/usr/bin/env bash
pip install code2logic --upgrade
pip install code2llm --upgrade

#code2logic ./ -f toon --compact --no-repeat-module --function-logic --with-schema --name project -o ./

source venv/bin/activate && python -m code2logic ./ -f toon --compact --name project -o ./
#source venv/bin/activate && python -m code2llm ./ -v -o ./project -m hybrid -f toon
source venv/bin/activate && python -m code2llm -f all
#code2llm ./ -f all
