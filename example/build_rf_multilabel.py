from sklearn.ensemble import RandomForestClassifier
import joblib

model_path = './model.joblib'

model = RandomForestClassifier()
model.fit([[1.,1.,5.], [2.,2.,5.], [3.,3.,1.]], [0, 2, 1])
to_save = dict(model=model,
               metadata={'features': [{'name': 'feature1', 'type': 'numeric', 'default': -1},
                                      {'name': 'feature2', 'type': 'numeric', 'default': -1},
                                      {'name': 'feature3', 'type': 'numeric', 'default': -1}]})

with open(model_path, 'wb') as fo:
    joblib.dump(to_save, fo)
