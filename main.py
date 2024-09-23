from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import db_helper
import generic_helper

app=FastAPI()

inprogress_orders={}

@app.post("/")
async def handle_request(request: Request):
        #Retrieve the JSON data from the request 
        payload=await request.json()

        # Extract the necessary information from the payload 
        # #based on the structure of the WebhookRequest from Dialogflow 
        intent = payload['queryResult']['intent']['displayName'] 
        parameters = payload['queryResult']['parameters'] 
        output_contexts = payload['queryResult']['outputContexts']

        session_id=generic_helper.extract_session_id(output_contexts[0]['name']) #1st element from output_context

        intent_handler_dict={
              'new.order':new_order,
              'order.add - context: ongoing-order':add_to_order,
              'order.complete - context : ongoing-order':complete_order,
              'order.remove - context: ongoing-order':remove_from_order,
              'track.order - context: ongoing-tracking':track_order
        }
        return intent_handler_dict[intent](parameters, session_id)


def new_order(parameters:dict,session_id:str):
      if session_id in inprogress_orders:
              del inprogress_orders[session_id]
      
      fulfillment_text = 'Starting new order. Specify Products and quantities. For example, you can say, "I would like to order two Four Pole ACB and one 3200A ACB Finger Contact. Also, we have only the following Products currently:Air Circuit Breaker, Winmaster 2 Air Circuit Breaker, Triple Pole Air Circuit Breaker, Four Pole ACB, ACB Circuit Breaker, 3200A ACB Finger Contact, 20A ACB Eaton.'
      return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })
      
            
def add_to_order(parameters:dict,session_id:str):
      product_name=parameters["product_name"]
      quantity=parameters["quantity"]

      if len(product_name)!=len(quantity):
                fulfillment_text= "Sorry i didn't understand. Can you please specify Product name and quantities clearly."
      else:
                new_product_dict=dict(zip(product_name,quantity))

                if session_id in inprogress_orders:
                        curr_dict=inprogress_orders[session_id]
                        curr_dict.update(new_product_dict)
                        inprogress_orders[session_id]=curr_dict

                else:
                       inprogress_orders[session_id]=new_product_dict
#                        inprogress_orders = {
#     session_id_1: {product_name_1: quantity_1, product_name_2: quantity_2, ...},
#     session_id_2: {product_name_a: quantity_a, product_name_b: quantity_b, ...},
#     ...
#}
                      

            #     print("************")
            #     print(inprogress_orders)

            #     fulfillment_text=f"Recieved {product_name} and {quantity}"
                 
                order_str=generic_helper.get_str_from_product_dict(inprogress_orders[session_id])
                fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

      return JSONResponse(content={
                "fulfillmentText": fulfillment_text
            })     


def save_to_db(order:dict):
        #order={"Four Pole ACB":2,"20A Acb Eaton":3}
        
      next_order_id= db_helper.get_next_order_id()

      for product_name, quantity in order.items():
               rcode=db_helper.insert_order_item(
                      product_name,
                      quantity,
                      next_order_id
               )
               if rcode == -1:
                  return -1

      # Now insert order tracking status      
      db_helper.insert_order_tracking(next_order_id,"in progress") 
      # print(db_helper.get_next_order_id()) 
      return next_order_id  
      
      
def complete_order(parameters:dict,session_id:str):
      if session_id not in inprogress_orders:
              fullfillment_text="I'm having a trouble finding your order. Sorry! Can you place a new order please?"
      else:
            order=inprogress_orders[session_id]
            order_id=save_to_db(order)
             
            if order_id == -1:
                  fullfillment_text="Sorry, I couldn't process your order due to a backend error "\
                    "Please place a new order again."
            else:
                  order_total=db_helper.get_total_order_price(order_id)

                  fulfillment_text = f"Awesome. We have placed your order. " \
                                     f"Here is your order id # {order_id}. " \
                                     f"Your order total is {order_total} which you can pay at the time of delivery!"
                  
            del inprogress_orders[session_id]   

      return JSONResponse(content={
                "fulfillmentText": fulfillment_text
            })
    

def remove_from_order(parameters:dict,session_id:str):
      if session_id not in inprogress_orders:
            return JSONResponse(content={
            "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
        })
      product_name=parameters["product_name"]
      current_order=inprogress_orders[session_id]
      
      #track removed items
      removed_items=[]
      not_such_items=[]

      for item in product_name:
            if item not in current_order:
                   not_such_items.append(item)        
            else:  
                   removed_items.append(item)        
                   del current_order[item]

      if len(removed_items)>0:
             fulfillment_text=f'Removed {",".join(removed_items)} from your order!'

      if len(not_such_items)>0:
             fulfillment_text=f'Your current order does not have{",".join(not_such_items)}'
      
      if len(current_order.keys())==0:
             fulfillment_text=f"Your order is empty!"
      else:
             order_str=generic_helper.get_str_from_product_dict(current_order)
             fulfillment_text+= f"Here is what is left in your order:{order_str}"
      
      return JSONResponse(content={
             "fulfillmentText":fulfillment_text
      })                


def track_order(parameters:dict,session_id:str):
      order_id=int(parameters['order_id'])
      order_status=db_helper.get_order_status(order_id)

      if order_status:
            fulfillment_text=f"The order status for order id:{order_id} is: {order_status}"
      else:
            fulfillment_text=f"No order found with order id:{order_id}"
            
      return JSONResponse(content={
                "fulfillmentText": fulfillment_text
            })
    

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)