#!/usr/bin/python

import sys
import pickle
sys.path.append("../tools/")

from feature_format import featureFormat, targetFeatureSplit
from tester import dump_classifier_and_data
from time import time
from sklearn.metrics import accuracy_score


### Selecting features
### features_list is a list of strings, each of which is a feature name.
### The first feature must be "poi".
features_list_original = ['poi','salary', 'deferral_payments', 'total_payments',
                 'loan_advances', 'bonus', 'restricted_stock_deferred',
                 'deferred_income', 'total_stock_value', 'expenses',
                 'exercised_stock_options', 'other', 'long_term_incentive',
                 'restricted_stock', 'director_fees', 'to_messages',
                 'from_poi_to_this_person', 'from_messages',
                 'from_this_person_to_poi', 'shared_receipt_with_poi']


### Loading the dictionary containing the dataset
with open("final_project_dataset.pkl", "r") as data_file:
    data_dict = pickle.load(data_file)


### Data exploration
data_points = len(data_dict)
print "Number of data points in dataset:", data_points
features = len(data_dict[data_dict.keys()[0]])
print "Number of features in the dataset:", features


### Looking for values that do not have value for any columns, to include in outliers and remove
for i in data_dict:
    content = False
    for v in data_dict[i]:
        if data_dict[i][v] == 'NaN':
            continue
        elif data_dict[i][v] == 0:
            continue
        content = True
    if not content:
        print "This person does not have any values in the dataset and will be removed:", i

    
### Removing outliers
data_dict.pop("TOTAL", 0) # spreadsheet feature
data_dict.pop("LOCKHART EUGENE E", 0) # all data 0 or NA, not helpful
data_dict.pop("TRAVEL AGENCY IN THE PARK", 0) # not a person


### Creating new features: the fractions of emails from POIs and to POIs
def features(dividend, divisor):
    new_list = []
    for i in data_dict:
        if data_dict[i][dividend] == "NaN" or data_dict[i][divisor] == "NaN":
            new_list.append(0.)
        elif data_dict[i][dividend] >= 0:
            new_list.append(float(data_dict[i][dividend])/float(data_dict[i][divisor]))
    return new_list

ratio_emails_to_poi = features("from_this_person_to_poi","from_messages")
ratio_emails_from_poi = features("from_poi_to_this_person", "to_messages")


### inserting ratio_emails_to_poi and ratio_emails_from_poi into data_dict            
count = 0
for i in data_dict:
    data_dict[i]["ratio_emails_to_poi"] = ratio_emails_to_poi[count]
    data_dict[i]["ratio_emails_from_poi"] = ratio_emails_from_poi[count]
    count += 1

features_list_original += ["ratio_emails_to_poi", "ratio_emails_from_poi"]


### Storing to my_dataset for easy export below   
my_dataset = data_dict


### Extracting features and labels from dataset for local testing
data = featureFormat(my_dataset, features_list_original, sort_keys = True)
labels, features = targetFeatureSplit(data)


#####################
# FEATURE SELECTION #
#####################
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.cross_validation import StratifiedKFold
from sklearn.feature_selection import RFECV
lr = LogisticRegression()

### Optimal number of features:
rfecv = RFECV(estimator=lr, step=1, cv=StratifiedKFold(labels, 3),
          scoring='precision')
rfecv.fit(features, labels)
print("Optimal number of features : %d" % rfecv.n_features_) #Answer: 5


'''
### Plotting number of features VS. cross-validation scores
plt.figure()
plt.xlabel("Number of features selected")
plt.ylabel("Cross validation score (nb of correct classifications)")
plt.plot(range(1, len(rfecv.grid_scores_) + 1), rfecv.grid_scores_)
plt.show()
'''


### Choosing the 5 most important features
from sklearn.feature_selection import SelectKBest
k_best = SelectKBest(k = 5)
k_best.fit(features, labels)

results = zip(features_list_original[1:], k_best.scores_)
results = sorted(results, key=lambda x: x[1], reverse=True)
print "K-best features in descending order:", results


### Selected the best features based on K-best scores in features_list
features_list = ['poi', 'exercised_stock_options', 'bonus',
                 'salary', 'ratio_emails_to_poi', 'deferred_income']


### Extract features and labels from dataset for local testing
data = featureFormat(my_dataset, features_list, sort_keys = True)
labels, features = targetFeatureSplit(data)


####################
# TRAIN/TEST SPLIT #
####################
from sklearn.model_selection import train_test_split
features_train, features_test, labels_train, labels_test = \
                train_test_split(features, labels, test_size=0.3, random_state=42)


###############
# CLASSIFIERS #
###############

### 1. Gaussian NB
from sklearn.naive_bayes import GaussianNB

clf = GaussianNB()
clf.fit(features_train, labels_train)
pred = clf.predict(features_test)

### TEST DATA SCORES
# Accuracy: 0.881
# Precision: 0.5
# Recall: 0.6

'''
### 2. Decision Tree
from sklearn import tree

#clf = tree.DecisionTreeClassifier(min_samples_split = 5, random_state = 150)
#clf = tree.DecisionTreeClassifier(min_samples_split = 10, random_state = 150)
clf = tree.DecisionTreeClassifier(min_samples_split = 15, random_state = 150)
#clf = tree.DecisionTreeClassifier(min_samples_split = 20, random_state = 150)
clf.fit(features_train, labels_train)
pred = clf.predict(features_test)

### TEST DATA SCORES
#Accuracy: 0.786, 0.833, 0.833, 0.833
#Precision: 0.167, 0.333, 0.375, 0.375
#Recall: 0.2, 0.4, 0.6, 0.6


### 3. RandomForest
from sklearn.ensemble import RandomForestClassifier

###default n_estimators=10 and min_samples_split=2
clf = RandomForestClassifier(random_state = 150)
#clf = RandomForestClassifier(min_samples_split = 3, random_state = 150)
#clf = RandomForestClassifier(min_samples_split = 4, random_state = 150)
#clf = RandomForestClassifier(n_estimators = 15, random_state = 150)
#clf = RandomForestClassifier(n_estimators = 15, min_samples_split = 3, random_state = 150)
#clf = RandomForestClassifier(n_estimators = 15, min_samples_split = 4, random_state = 150)
#clf = RandomForestClassifier(n_estimators = 20, random_state = 150)
clf = RandomForestClassifier(n_estimators = 20, min_samples_split = 3, random_state = 150)
#clf = RandomForestClassifier(n_estimators = 20, min_samples_split = 4, random_state = 150)
clf.fit(features_train, labels_train)
pred = clf.predict(features_test)

### TEST DATA SCORES
#Accuracy: 0.881, 0.881, 0.881, 0.905, 0.929, 0.905, 0.881, 0.905, 0.905
#Precision: 0.5, 0.5, 0.5, 0.667, 0.75, 0.667, 0.5, 0.667, 0.667
#Recall: 0.2, 0.2, 0.4, 0.4, 0.6, 0.2, 0.4, 0.2, 0.4, 0.4

### BASED ON STRATIFIED-K-FOLD from tester.py
#Accuracy: 0.852, 0.856, 0.857, 0.856, 0.86, 0.859, 0.856, 0.859, 0.86 
#Precision: 0.458, 0.490, 0.495, 0.488, 0.522, 0.518, 0.491, 0.513, 0.522
#Recall: 0.184, 0.206, 0.232, 0.233, 0.233, 0.236, 0.184, 0.211, 0.229
'''


print "Accuracy score:", accuracy_score(pred, labels_test)

### Tune your classifier to achieve better than .3 precision and recall 
### using our testing script. Check the tester.py script in the final project
### folder for details on the evaluation method, especially the test_classifier
### function. Because of the small size of the dataset, the script uses
### stratified shuffle split cross validation. For more info: 
### http://scikit-learn.org/stable/modules/generated/sklearn.cross_validation.StratifiedShuffleSplit.html
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
print precision_score(labels_test, pred)
print recall_score(labels_test, pred)


### Number of POIs/Non-POIs in the test data
count = 0
for poi in labels_test:
    if poi == 1:
        count += 1

print "Number of POIs in the test data:", count #Answer: 5
print "Total number of people in the test data:", len(features_test) #Answer: 42


### Dump your classifier, dataset, and features_list so anyone can
### check your results. You do not need to change anything below, but make sure
### that the version of poi_id.py that you submit can be run on its own and
### generates the necessary .pkl files for validating your results.
dump_classifier_and_data(clf, my_dataset, features_list)
