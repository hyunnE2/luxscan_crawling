from datetime import datetime 



file = open('/home/hyunnE2/luxscan_crawling/test.log', 'a', encoding='euc-kr')
file.write('start\n')

print(datetime.now())

file.close()


