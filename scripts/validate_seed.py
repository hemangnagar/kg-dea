import json
import yaml
from inteldoc.world import ROOT
from inteldoc.seed import validate_seed

if __name__=='__main__':
    print(json.dumps(validate_seed(yaml.safe_load((ROOT/'world/seed.yaml').read_text())),indent=2))
