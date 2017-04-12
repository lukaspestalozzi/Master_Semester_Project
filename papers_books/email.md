Hey Igor

I've done some research and found several promising papers and projects.

Based on those papers I am confident that a approach with (Expecty)MiniMax and a Neural network as heuristic function is a promising way to go.

**Here are the most important insights from the appended papers:**

- The _AI-Tichu-2013_ file is a (german) student project done in 2013 that created a AI for Tichu using a fine tuned and rather complicated Heuristics to determine the next move. They basically used a minimax with search-depth 1. At the end they reach about human player strength. It has some interesting concepts and shows that it's possible to reach human level play. But their heuristics are all fine tuned and contain some thresholds that have to be set manually and strongly impact the play strength.

Then I found a game that is very similar to Tichu: _Fight the Landlord (Dou Di Zhu)_.
There are some crucial differences but the overall game is the same. The most important differences are:
- Tichu is played 2 vs 2 while Dou Di Zhu is 2 vs 1.
- In Dou Di Zhu there is a bidding phase at the beginning to determine who is the Landlord (the 1 player playing alone).
- In Tichu at the beginning each player has to give one card to each other player.
- In Dou Di Zhu there are more possible card combinations that can be played (Tichu can play a subset of them).
- Tichu has 4 special cards (52 normal + 4 special) while Dou Di Zhu has 52 normal + 2 jokers.
- In Tichu you can announce at the beginning that you will win this round (this is called to announce a 'Tichu'). If you finish first this gives 100 points, if not you loose 100.

All in all, Tichu has a smaller fanout (less possible moves) and there are more players -> less cards per player.
But the 4 special cards, the card swaping and the 'Tichu' announcement increases the tactical possibilities.

- _Fight the Landlord_Final Report_ is a student project that creates 4 Agents (Random, Simple, Advanced, Predictive) to play Dou Di Zhu. The Predictive and Advanced agents can challenge human players.
They use minimax with a rather simple heuristic function enriched with some 'human experience'.
They tried a neural network agent but gave up because their network did not converge after 2 days of training.

The other papers are concerned with Monte Carlo Tree Search for imperfect information games. In particular _Information-Set-Monte-Carlo-Tree-Search-2012_ shows that in Dou Di Zhu it is seldom a big advantage to know the enemies cards and that Monte Carlo is not better than minimax in that game. I assume it is the same for Tichu.

**Plan**

The goal is to create an agent that can challenge human players. It uses (expecti)minimax with a Neural Network as heuristic function. The NN learns by playing against itself.

A secondary goal is to keep the agent somewhat general so that it is easy to adapt it to other games.

Like in _Fight the Landlord_Final Report_ I want to start with a Random Agent that plays a random legal move. That includes the implementation of the whole game-logic and the platform. Ideally I find some framework or App that already exist that I can use. If not, then I will create a small CLI to interact with the agent.
Once that is set up I integrate the minimax search and a simple heuristic (Simple Agent). Here I have to think about to what degree I want to consider the enemies moves.
Then I start to create the Neural Network and train it -> NN Agent.
Depending how well that works I can proceed to add stuff like inferring other players cards, expectiminimax, add more advanced teamplay etc...

**challenges**

Some challenges I see:
- Train the heuristic NN: I'd bootstrap it with a simple heuristic (maybe one from  _Fight the Landlord_Final Report_) and then let the agent play against itself to improve the NN.
- Deal with the uncertainty and the resulting big fanout: maybe use expectiminimax and try to infer the enemies cards. Prune the tree based on probabilities and already played cards. Maybe similar to [Giraffe](https://arxiv.org/pdf/1509.01549v2.pdf)
- Teamplay: Start with very easy rules like 'don't play when my teammate played the highest cards'.
- Special cards: I somehow have to integrate them without making the fanout of the search too big. Some cards need special reasoning to be used efficiently. I hope the NN can deal with it in the heuristic function.
- Card swapping at the beginning: I'll start again with a simple rule and when I know more about the game introduce more sophisticated tactics. Ideally again a self learned heuristic.
- When to announce 'Tichu': I hope I can take the NN and define a threshold.
