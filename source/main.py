import ib

if __name__ == "__main__":
    store = ib.Store(port=4002, clientId=1001)
    store.disconnect()
