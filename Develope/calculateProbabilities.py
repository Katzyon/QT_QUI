
def calculateRatioProbabilities(ngroups, probability_ratio):
    """ Calculate the probability of ngroups to appear based on the probability_ratio. The first group 
    appears with high probability and the probability decreases by probability ratio for the following groups."""
    
    # Initialize a list to hold the probabilities
    probabilities = []
    
    # Calculate the base probability for the first image
    base_prob = 1.0
    total_prob = 0.0
    
    # Calculate the probabilities for each image
    for i in range(ngroups):
        prob = base_prob / (probability_ratio ** i)
        probabilities.append(prob)
        total_prob += prob
    
    # Normalize the probabilities to sum to 1
    probabilities = [prob / total_prob for prob in probabilities]
    
    return probabilities

