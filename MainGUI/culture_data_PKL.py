import pickle

file_path = r"D:\DATA\Patterns\27081\Culture\Protocols\Protocol_4\protocol_4.pkl"

with open(file_path, "rb") as f:
    data = pickle.load(f)

print(type(data))
