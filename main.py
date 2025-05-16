import os

import hydra

from api_keys import *
from bench.config import Config
from bench.pillager_bench import PillagerBench


@hydra.main(config_path="configs", config_name="benchmark", version_base="1.3")
def main(args: Config):
    # set openai api key
    os.environ["OPENAI_API_KEY"] = openai_api_key
    os.environ["DEEPSEEK_API_KEY"] = deepseek_api_key
    os.environ["OPENROUTER_API_KEY"] = openrouter_api_key

    bench = PillagerBench(args)
    bench.run()

if __name__ == "__main__":
    main()
