import re

#Extracting Session id  
def extract_session_id(session_str:str):
       match=re.search(r"/sessions/(.*?)/contexts/",session_str)  # \/sessions\/(.*)\/contexts\/
       if match: 
              extracted_string=match.group(1)
              return extracted_string
       
       return ""



#convert to (item1:2)from dict to (2 item1) in this format
def get_str_from_product_dict(product_name:dict):
    result = ", ".join([f"{int(value)} {key}" for key, value in product_name.items()])
    return result




if __name__=="__main__":
       print(get_str_from_product_dict({"Four Pole ACB":3, "Air Circuit Breaker":5}))
       print(extract_session_id("projects/c-selectric-qycq/agent/sessions/64d4d1cc-7051-160d-e5b9-e1f15aaf78cf/contexts/ongoingorder"))
