from summarizer import Summarizer, OllamaWrapper
from pusher import Pusher
from config import *
from openai import OpenAI
import argparse
import os


def main(api_server: str="aliyun", model: str="deepseek-r1",
         max_results: int=8, workload: bool=False, rate_local: bool=False, batch_inference: bool=True):
    if api_server == "ollama":
        if workload:
            raise ValueError("Can't use ollama when machine is under workload.")
        client = OllamaWrapper()
        api_type = "ollama"
    elif api_server == "siliconflow":
        client = OpenAI(api_key=SILICONFLOW_API_KEY, base_url=SILICONFLOW_BASE_URL)
        api_type = "openai"
    elif api_server == "deepseek":
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        api_type = "openai"
    elif api_server == "google":
        client = OpenAI(api_key=GOOGLE_API_KEY, base_url=GOOGLE_BASE_URL)
        api_type = "openai"
    elif api_server == "aliyun":
        client = OpenAI(api_key=ALIYUN_API_KEY, base_url=ALIYUN_BASE_URL)
        api_type = "openai"
    
    # Batch inference supported by aliyun now. Not sure about other providers.
    batch_inference = batch_inference if api_server == "aliyun" else False

    if rate_local:
        client_rate = OllamaWrapper()
        model_rate = "qwen2.5-coder:7b"
        api_type_rate = "ollama"
    else:
        client_rate = OpenAI(api_key=SILICONFLOW_API_KEY,base_url=SILICONFLOW_BASE_URL)
        model_rate = "THUDM/glm-4-9b-chat"
        api_type_rate = "openai"
    
    print("-----------Start of Task-----------")
    print(f"API server: {api_server}, model: {model}, rate local = {rate_local}, batch inference = {batch_inference}")
    summarizer = Summarizer(client, client_rate, model, model_rate, api_type, api_type_rate, max_results, workload)
    pusher = Pusher()
    try:
        if batch_inference:
            content = summarizer.compile_batch()
        else:
            content = summarizer.compile()
        if not os.path.exists(summarizer.path + ".pdf"):
            raise FileNotFoundError("PDF output missing.")
        pusher.push_to_email()
    except Exception as e:
        pusher.push_error_message(e)
    print("------------End of Task------------\n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize arxiv papers using different API servers.")

    parser.add_argument('--api_server', type=str, default="aliyun",
                        choices = ["ollama","siliconflow","deepseek","google","aliyun"],
                        help="API server (ollama, siliconflow, deepseek, google, aliyun)")
    parser.add_argument('--model', type=str, default="deepseek-r1",
                        help = "model used.")
    parser.add_argument('--max_results', type=int, default=8,
                        help="maximum number of summaries to be generated.")
    parser.add_argument('--workload', action='store_true',
                        help="whether to use api for rating.")
    parser.add_argument('--rate_local', action='store_true',
                        help="whether to rate locally.")
    parser.add_argument('--batch_inference', action='store_true',
                        help="whether to use batch inference with aliyun api.")
    
    args = parser.parse_args()

    main(args.api_server, args.model, args.max_results, args.workload, args.rate_local, args.batch_inference)