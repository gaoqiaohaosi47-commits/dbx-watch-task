import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp()

@app.timer_trigger(schedule="* * * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def timerTrigger(myTimer: func.TimerRequest) -> None:
    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('[実行完了]Python timer trigger function executed.')