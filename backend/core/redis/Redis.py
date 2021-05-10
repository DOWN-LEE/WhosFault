import redis
import datetime

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DBNUM = 0

class RedisQueue(object):
    """
        Redis Lists are an ordered list, First In First Out Queue
        Redis List pushing new elements on the head (on the left) of the list.
        The max length of a list is 4,294,967,295
    """
    def __init__(self, name):
        """
            host='localhost', port=6379, db=0
        """
        self.key = name
        self.rq = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DBNUM)

    def size(self): # 큐 크기 확인
        return self.rq.llen(self.key)

    def isEmpty(self): # 비어있는 큐인지 확인
        return self.size() == 0

    def push(self, element): # 데이터 넣기
        self.rq.rpush(self.key, element)
    
    def pop(self):
        self
    
    def getlist(self, num):
        ans = []
        for _ in range(num):
            x = self.rq.lpop(self.key)
            if(x==None):
                break
            ans.append(x.decode())
        return ans
        #return self.rq.lrange(self.key, 0, num)
    
    def setval(self, key, value):
        self.rq.set(key, str(value), datetime.timedelta(seconds=100))


    # def get(self, isBlocking=False, timeout=None): # 데이터 꺼내기
    #     if isBlocking:
    #         element = self.rq.brpop(self.key, timeout=timeout) # blocking right pop
    #         element = element[1] # key[0], value[1]
    #     else:
    #         element = self.rq.rpop(self.key) # right pop
    #     return element

    # def get_without_pop(self): # 꺼낼 데이터 조회
    #     if self.isEmpty():
    #         return None
    #     element = self.rq.lindex(self.key, -1)
    #     return element
    def exist_by_key(self, key):
        return self.rq.exists(key)

    def get_by_key(self, key):
        return self.rq.get(key)
    
    def del_by_key(self, key):
        self.rq.delete(key)




if __name__ == '__main__':
    q = RedisQueue("sibal")
    print(q.rq.lpop("sibal").decode())