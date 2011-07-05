from math import sqrt, floor
import Orange.core as orange
import Orange
import Orange.feature.scoring
import random
import copy

def _default_small_learner(attributes=None, rand=None, base=None):
    """ A helper function for constructing a small tree learner for use
    in the RandomForestLearner.
    :param instances: data - to select the measure.
    :param attributes: number of features used in a randomly drawn
            subset when searching for best feature to split the node
            in tree growing
    :type attributes: int
    :param rand: random generator used in feature subset selection in split constructor. 
            If None is passed, then Python's Random from random library is 
            used, with seed initialized to 0.
    :type rand: function
    """
    # tree learner assembled as suggested by Breiman (2001)
    if not base:
        base = Orange.classification.tree.TreeLearner(
            storeNodeClassifier=0, storeContingencies=0, 
            storeDistributions=1, minExamples=5)

    return _RandomForestTreeLearner(base=base, attributes=attributes, rand=rand)

class RandomForestLearner(orange.Learner):
    """
    Just like bagging, classifiers in random forests are trained from bootstrap
    samples of training data. Here, classifiers are trees. However, to increase
    randomness, classifiers are built so that at each node the best feature is
    chosen from a subset of features in the training set. We closely follow the
    original algorithm (Brieman, 2001) both in implementation and parameter
    defaults.
        
    :param trees: number of trees in the forest.
    :type trees: int
    :param attributes: number of features used in a randomly drawn
            subset when searching for best feature to split the node in
            tree growing (default: None, and if kept this way, this is
            turned into square root of the number of features in the
            training set, when this is presented to learner). Ignored
            if :obj:`learner` is specified.
    :type attributes: int
    :param base_learner: A base tree learner. If None (default),
        :class:`~Orange.classification.tree.TreeLearner` with Gini index
        or MSE for attribute scoring will be used, and it will not split
        nodes with less than 5 data instances. The base learner will be
        randomized with Random Forest's random attribute subset selection.
    :type base_learner: None or :class:`Orange.classification.tree.TreeLearner`
    :param rand: random generator used in bootstrap sampling. If None is 
        passed, then Python's Random from random library is used, with seed
        initialized to 0.
    :param learner: Tree induction learner. If None (default), 
        the :obj:`~ScoreFeature.base_learner` will be used (and randomized). If
        :obj:`~ScoreFeature.learner` is specified, it will be used as such
        with no additional transformations.
    :type learner: None or :class:`Orange.core.Learner`
    :param callback: a function to be called after every iteration of
            induction of classifier. This is called with parameter 
            (from 0.0 to 1.0) that gives estimates on learning progress.
    :param name: name of the learner.
    :type name: string
    :rtype: :class:`~Orange.ensemble.forest.RandomForestClassifier` or 
            :class:`~Orange.ensemble.forest.RandomForestLearner`
    """

    def __new__(cls, instances=None, weight = 0, **kwds):
        self = orange.Learner.__new__(cls, **kwds)
        if instances:
            self.__init__(**kwds)
            return self.__call__(instances, weight)
        else:
            return self

    def __init__(self, trees=100, attributes=None,\
                    name='Random Forest', rand=None, callback=None, base_learner=None, learner=None):
        self.trees = trees
        self.name = name
        self.learner = learner
        self.attributes = attributes
        self.callback = callback
        self.rand = rand
        self.base_learner = base_learner
        
        if not self.rand:
            self.rand = random.Random(0)
            
        self.randstate = self.rand.getstate() #original state

    def __call__(self, instances, weight=0):
        """
        Learn from the given table of data instances.
        
        :param instances: data instances to learn from.
        :type instances: class:`Orange.data.Table`
        :param origWeight: weight.
        :type origWeight: int
        :rtype: :class:`Orange.ensemble.forest.RandomForestClassifier`
        """
        
        if not self.learner:
            learner = _default_small_learner(self.attributes, self.rand, base=self.base_learner)
        else:
            learner = self.learner
        
        self.rand.setstate(self.randstate) #when learning again, set the same state

        n = len(instances)
        # build the forest
        classifiers = []
        for i in range(self.trees):
            # draw bootstrap sample
            selection = []
            for j in range(n):
                selection.append(self.rand.randrange(n))
            data = instances.get_items_ref(selection)
            # build the model from the bootstrap sample
            classifiers.append(learner(data, weight))
            if self.callback:
                self.callback()
            # if self.callback: self.callback((i+1.)/self.trees)

        return RandomForestClassifier(classifiers = classifiers, name=self.name,\
                    domain=instances.domain, classVar=instances.domain.classVar)
 

class RandomForestClassifier(orange.Classifier):
    """
    Random forest classifier uses decision trees induced from bootstrapped
    training set to vote on class of presented instance. Most frequent vote
    is returned. However, in our implementation, if class probability is
    requested from a classifier, this will return the averaged probabilities
    from each of the trees.

    When constructing the classifier manually, the following parameters can
    be passed:

    :param classifiers: a list of classifiers to be used.
    :type classifiers: list
    
    :param name: name of the resulting classifier.
    :type name: str
    
    :param domain: the domain of the learning set.
    :type domain: :class:`Orange.data.Domain`
    
    :param classVar: the class feature.
    :type classVar: :class:`Orange.data.variable.Variable`

    """
    def __init__(self, classifiers, name, domain, classVar, **kwds):
        self.classifiers = classifiers
        self.name = name
        self.domain = domain
        self.classVar = classVar
        self.__dict__.update(kwds)

    def __call__(self, instance, resultType = orange.GetValue):
        """
        :param instance: instance to be classified.
        :type instance: :class:`Orange.data.Instance`
        
        :param result_type: :class:`Orange.classification.Classifier.GetValue` or \
              :class:`Orange.classification.Classifier.GetProbabilities` or
              :class:`Orange.classification.Classifier.GetBoth`
        
        :rtype: :class:`Orange.data.Value`, 
              :class:`Orange.statistics.Distribution` or a tuple with both
        """
        from operator import add
        
        # handle discreete class
        
        if self.class_var.var_type == Orange.data.variable.Discrete.Discrete:
        
            # voting for class probabilities
            if resultType == orange.GetProbabilities or resultType == orange.GetBoth:
                prob = [0.] * len(self.domain.classVar.values)
                for c in self.classifiers:
                    a = [x for x in c(instance, orange.GetProbabilities)]
                    prob = map(add, prob, a)
                norm = sum(prob)
                cprob = Orange.statistics.distribution.Discrete(self.classVar)
                for i in range(len(prob)):
                    cprob[i] = prob[i]/norm
                
            # voting for crisp class membership, notice that
            # this may not be the same class as one obtaining the
            # highest probability through probability voting
            if resultType == orange.GetValue or resultType == orange.GetBoth:
                cfreq = [0] * len(self.domain.classVar.values)
                for c in self.classifiers:
                    cfreq[int(c(instance))] += 1
                index = cfreq.index(max(cfreq))
                cvalue = Orange.data.Value(self.domain.classVar, index)
    
            if resultType == orange.GetValue: return cvalue
            elif resultType == orange.GetProbabilities: return cprob
            else: return (cvalue, cprob)
        
        else:
            # Handle continuous class
            
            # voting for class probabilities
            if resultType == orange.GetProbabilities or resultType == orange.GetBoth:
                probs = [c(instance, orange.GetProbabilities) for c in self.classifiers]
                cprob = dict()
                for prob in probs:
                    a = dict(prob.items())
                    cprob = dict( (n, a.get(n, 0)+cprob.get(n, 0)) for n in set(a)|set(cprob) )
                cprob = Orange.statistics.distribution.Continuous(cprob)
                cprob.normalize()
                
            # gather average class value
            if resultType == orange.GetValue or resultType == orange.GetBoth:
                values = [c(instance).value for c in self.classifiers]
                cvalue = Orange.data.Value(self.domain.classVar, sum(values) / len(self.classifiers))
            
            if resultType == orange.GetValue: return cvalue
            elif resultType == orange.GetProbabilities: return cprob
            else: return (cvalue, cprob)
            
    def __reduce__(self):
        return type(self), (self.classifiers, self.name, self.domain, self.classVar), dict(self.__dict__)

### MeasureAttribute_randomForests

class ScoreFeature(orange.MeasureAttribute):
    """
    :param trees: number of trees in the forest.
    :type trees: int
    :param attributes: number of features used in a randomly drawn
            subset when searching for best feature to split the node in
            tree growing (default: None, and if kept this way, this is
            turned into square root of the number of features in the
            training set, when this is presented to learner). Ignored
            if :obj:`learner` is specified.
    :type attributes: int
    :param base_learner: A base tree learner. If None (default),
        :class:`~Orange.classification.tree.TreeLearner` with Gini index
        or MSE for attribute scoring will be used, and it will not split
        nodes with less than 5 data instances. The base learner will be
        randomized with Random Forest's random attribute subset selection.
    :type base_learner: None or :class:`Orange.classification.tree.TreeLearner`
    :param rand: random generator used in bootstrap sampling. If None is 
        passed, then Python's Random from random library is used, with seed
        initialized to 0.
    :param learner: Tree induction learner. If None (default), 
        the :obj:`~ScoreFeature.base_learner` will be used (and randomized). If
        :obj:`~ScoreFeature.learner` is specified, it will be used as such
        with no additional transformations.
    :type learner: None or :class:`Orange.core.Learner`
    """
    def __init__(self, trees=100, attributes=None, rand=None, base_learner=None, learner=None):

        self.trees = trees
        self.learner = learner
        self._bufinstances = None
        self.attributes = attributes
        self.rand = rand
        self.base_learner = base_learner
        if not self.rand:
            self.rand = random.Random(0)
        if self.learner == None:
            self.learner = _default_small_learner(attributes=self.attributes, rand=self.rand, base=self.base_learner)
  
    def __call__(self, feature, instances, apriorClass=None):
        """
        Return importance of a given feature.
        Only the first call on a given data set is computationally expensive.
        
        :param feature: feature to evaluate (by index, name or
            :class:`Orange.data.variable.Variable` object).
        :type feature: int, str or :class:`Orange.data.variable.Variable`.
        
        :param instances: data instances to use for importance evaluation.
        :type instances: :class:`Orange.data.Table`
        
        :param apriorClass: not used!
        
        """
        attrNo = None

        if type(feature) == int: #by attr. index
          attrNo  = feature
        elif type(feature) == type("a"): #by attr. name
          attrName = feature
          attrNo = instances.domain.index(attrName)
        elif isinstance(feature, Orange.data.variable.Variable):
          atrs = [a for a in instances.domain.attributes]
          attrNo = atrs.index(feature)
        else:
          raise Exception("MeasureAttribute_rf can not be called with (\
                contingency,classDistribution, apriorClass) as fuction arguments.")

        self._buffer(instances)

        return self._avimp[attrNo]*100/self._acu

    def importances(self, table):
        """
        DEPRECATED. Return importance of all features in the dataset as a list. 
        
        :param table: dataset of which the features' importance needs to be
            measured.
        :type table: :class:`Orange.data.Table` 

        """
        self._buffer(table)
        return [a*100/self._acu for a in self._avimp]

    def _buffer(self, instances):
        """
        Recalculate importance of features if needed (ie. if it has been
        buffered for the given dataset yet).

        :param table: dataset of which the features' importance needs to be
            measured.
        :type table: :class:`Orange.data.Table` 

        """
        if instances != self._bufinstances or \
            instances.version != self._bufinstances.version:

            self._bufinstances = instances
            self._avimp = [0.0]*len(self._bufinstances.domain.attributes)
            self._acu = 0
            self._importanceAcu(self._bufinstances, self.trees, self._avimp)
      
    def _getOOB(self, instances, selection, nexamples):
        ooblist = filter(lambda x: x not in selection, range(nexamples))
        return instances.getitems(ooblist)

    def _numRight(self, oob, classifier):
        """
        Return a number of instances which are classified correctly.
        """
        #TODO How to accomodate regression?
        return sum(1 for el in oob if el.getclass() == classifier(el))
    
    def _numRightMix(self, oob, classifier, attr):
        """
        Return a number of instances which are classified 
        correctly even if a feature is shuffled.
        """
        perm = range(len(oob))
        self.rand.shuffle(perm)

        def shuffle_ex(index):
            ex = Orange.data.Instance(oob[index])
            ex[attr] = oob[perm[index]][attr]
            return ex
        #TODO How to accomodate regression?
        return sum(1 for i in range(len(oob)) if oob[i].getclass() == classifier(shuffle_ex(i)))

    def _importanceAcu(self, instances, trees, avimp):
        """Accumulate avimp by importances for a given number of trees."""
        n = len(instances)

        attrs = len(instances.domain.attributes)

        attrnum = {}
        for attr in range(len(instances.domain.attributes)):
           attrnum[instances.domain.attributes[attr].name] = attr            
   
        # build the forest
        classifiers = []  
        for i in range(trees):
            # draw bootstrap sample
            selection = []
            for j in range(n):
                selection.append(self.rand.randrange(n))
            data = instances.getitems(selection)
            
            # build the model from the bootstrap sample
            cla = self.learner(data)

            #prepare OOB data
            oob = self._getOOB(instances, selection, n)
            
            #right on unmixed
            right = self._numRight(oob, cla)
            
            presl = list(self._presentInTree(cla.tree, attrnum))
                      
            #randomize each feature in data and test
            #only those on which there was a split
            for attr in presl:
                #calculate number of right classifications
                #if the values of this features are permutated randomly
                rightimp = self._numRightMix(oob, cla, attr)                
                avimp[attr] += (float(right-rightimp))/len(oob)
        self._acu += trees  

    def _presentInTree(self, node, attrnum):
        """Return features present in tree (features that split)."""
        if not node:
          return set([])

        if  node.branchSelector:
            j = attrnum[node.branchSelector.classVar.name]
            cs = set([])
            for i in range(len(node.branches)):
                s = self._presentInTree(node.branches[i], attrnum)
                cs = s | cs
            cs = cs | set([j])
            return cs
        else:
          return set([])

class _RandomForestTreeLearner(Orange.core.Learner):
    """ A learner which wraps an ordinary TreeLearner with
    a new split constructor.
    """

    def __new__(cls, examples = None, weightID = 0, **argkw):
        self = Orange.core.Learner.__new__(cls, **argkw)
        if examples:
            self.__init__(**argkw)
            return self.__call__(examples, weightID)
        else:
            return self
      
    def __init__(self, base, attributes, rand):
        self.base = base
        self.attributes = attributes
        self.rand = rand
        if not self.rand: #for all the built trees
            self.rand = random.Random(0)
    
    def __call__(self, examples, weight=0):
        """ A current tree learner is copied, modified and then used.
        Modification: set a different split constructor, which uses
        a random subset of attributes.
        """
        bcopy = copy.copy(self.base)

        #if base tree learner has no measure set
        if not bcopy.measure:
            bcopy.measure = Orange.feature.scoring.Gini() \
                if isinstance(examples.domain.class_var, Orange.data.variable.Discrete) \
                else Orange.feature.scoring.MSE()

        bcopy.split = SplitConstructor_AttributeSubset(\
            bcopy.split, self.attributes, self.rand)

        return bcopy(examples, weight=weight)

class SplitConstructor_AttributeSubset(orange.TreeSplitConstructor):
    def __init__(self, scons, attributes, rand = None):
        self.scons = scons           # split constructor of original tree
        self.attributes = attributes # number of features to consider
        self.rand = rand
        if not self.rand:
            self.rand = random.Random(0)

    def __call__(self, gen, weightID, contingencies, apriori, candidates, clsfr):
        # if number of features for subset is not set, use square root
        if not self.attributes:
            self.attributes = int(sqrt(len(candidates)))

        cand = [1]*self.attributes + [0]*(len(candidates) - self.attributes)
        self.rand.shuffle(cand)
        # instead with all features, we will invoke split constructor 
        # only for the subset of a features
        t = self.scons(gen, weightID, contingencies, apriori, cand, clsfr)
        return t
