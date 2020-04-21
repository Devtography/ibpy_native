from ib import IBStore

if __name__ == "__main__":
    store = IBStore(port=4002, clientId=1001)
    store.disconnect()
