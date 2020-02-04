from fastapi import FastAPI

app = FastAPI()


@app.post("/")
def set_root():
    return None
    return {
        "models": {
            "clean": [
                {"name": "hefesto_core.timeserie", "filter": {"plugin": "22"}}
            ],
            "update": [
                {
                    "name": "hefesto_core.timeserie",
                    "filter": {"plugin": "fsfdsfd"},
                    "fields": {"context": {"Hola": "Mundo"}},
                }
            ],
            "fixtures": [
                {
                    "model": "hefesto_core.timeserie",
                    "pk": 9865,
                    "fields": {
                        "time": "2020-02-02T14:54:23Z",
                        "name": "test",
                        "value": 51.0,
                        "plugin": "fsfdsfd",
                        "context": {"Hola": "Mundo"},
                        "exported": False,
                        "created": "2020-02-02T14:54:38.337Z",
                        "updated": "2020-02-02T15:18:55.243Z",
                    },
                },
                {
                    "model": "hefesto_core.timeserie",
                    "pk": 9365,
                    "fields": {
                        "time": "2020-02-02T15:59:48Z",
                        "name": "gfhfg",
                        "value": 545.0,
                        "plugin": "fghgfhfghgfh",
                        "context": {},
                        "exported": False,
                        "created": "2020-02-02T15:09:54.961Z",
                        "updated": "2020-02-02T15:14:09.150Z",
                    },
                },
            ],
        }
    }


@app.get("/")
def read_root():
    return {"Hello": "World"}
