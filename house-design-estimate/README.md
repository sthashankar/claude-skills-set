# house-design-estimate (skill toolkit)
Works for any country: the user supplies the site, building codes, currency and rates (blank templates: data/codes_template.json,
data/rates_template.json). The rates and codes named *_sample.json in data/ are for demos only.
Skill: SKILL.md. Scripts in scripts/, page templates in templates/, rate book in data/, rules in references/, subagent role prompts in references/agents/,
a complete sample design in examples/sample_house.json.
Quick test:  cd scripts && python3 make_all.py ../examples/sample_house.json /tmp/out --png
