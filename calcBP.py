import pika, sys, os
import requests
from dotenv import load_dotenv

load_dotenv()

tensao = []
pico = []
vale = []
SBP_inicial = 0
DBP_inicial = 0
gain = 100

SESSION_URL = os.environ['SESSION_API']

def main():
    connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rabbitmq', connection_attempts=10, retry_delay=5))

    
    channel = connection.channel()

    channel.queue_declare(queue='tensao')
    channel.queue_declare(queue='sis_dia')
    

    def callback(ch, method, properties, body):
        global tensao
        global pico
        global vale
        global DBP_inicial
        global SBP_inicial

        if(SBP_inicial==0):
            r = requests.get(SESSION_URL)
            SBP_inicial = r.json()["data"]["session"]['sistolica']
            DBP_inicial = r.json()["data"]["session"]['diastolica']

        tensao.append(float(body))
        if(len(tensao)==150):
            min_value = min(tensao)
            max_value = max(tensao)
            pico.append(max_value)
            vale.append(min_value)
            tensao = []
            if(len(pico)==2):
                d = pico[1] - pico[0]
                d = d*1000
                d = d/0.5
                d = d/gain
                delta_SBP = d + SBP_inicial
                pico = []
                SBP_inicial = delta_SBP
            if(len(vale)==2):
                d = vale[1] - vale[0]
                d = d*1000
                d = d/0.5
                d = d/gain
                delta_DBP = d + DBP_inicial
                vale = []
                DBP_inicial = delta_DBP
            print("SBP: " + str(SBP_inicial) + " DBP: " + str(DBP_inicial))
            r = requests.patch(SESSION_URL, json = {"sistolica": SBP_inicial, "diastolica": DBP_inicial})
            channel.basic_publish(exchange='',
                          routing_key='sis_dia',
                          body="SBP: " + str(SBP_inicial) + " DBP: " + str(DBP_inicial))
            SBP_inicial = 0
        # print(" [x] Received " + str(body))
        

    channel.basic_consume(queue='tensao', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)