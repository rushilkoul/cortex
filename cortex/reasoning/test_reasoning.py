from halo import Halo

with Halo(text="\033[2mloading language model...\033[0m", spinner="dots"):
    from cortex.shared.models import LocalLLM
    llm = LocalLLM()
    
while True:
    query = input("\033[96m>\033[0m ")
    with Halo(text="\033[2mAssimilating...\033[0m", spinner="dots"):
        answer = llm.generate(query)
    print(answer)
    