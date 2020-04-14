import ib

if __name__ == "__main__":
    store = ib.IBStore(port=4002, clientId=1001)
    store.disconnect()
