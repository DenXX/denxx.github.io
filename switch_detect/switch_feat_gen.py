import argparse
import sklearn
from numpy import std, mean, median
from itertools import groupby
from sys import argv

NOCLICKTIME = 10000
LAST_CLICK_DWELL = 1000
LONG_DWELL = 500
SHORT_DWELL = 200
EPS = 0.001

user_filter = set([])
query_filter = set([])
url_filter = set([])

class SessionStats:
    def __init__(self, session):
        self.day = session["day"]
        self.queries_count = 0
        self.clicks_count = 0
        self.actions_count = 0
        self.time_1click = NOCLICKTIME
        self.abandoned = 0
        self.ave_dwell = 0
        self.max_dwell = 0
        self.min_dwell = 0
        self.clicks_per_query = 0
        self.duration = 0
        self.unique_queries = 0
        self.duration_per_query = 0
        self.duration_per_action = 0
        self.min_pause = 0
        self.ave_pause = 0
        self.max_pause = 0
        self.pauses = []
        self.dwells = []
        self.query_ave_click_pos = {}
        self.ave_click_pos = 0.0
        self.max_click_per_query = 0
        self.long_dwell_clicks = 0
        self.short_dwell_clicks = 0
        self.time_between_clicks = 0
        self.is_last_click = 0
        self.is_last_query = 0
        self.is_last_switch = 0
        self.action_seq = ""
        self.extended_seq = ""
        self.extended_seq2 = ""
        self.time_to_switch = 0.0

        self.query_right_before_switch = -1
        self.queries_before_switch = set([])
        self.urls_right_before_switch = set([])
        self.urls_before_switch = set([])

        self.qu_ctr = {}
        self.qu_satctr = {}
        self.qu_lastctr = {}
        self.qu_dsatctr = {}

        self.q_ctr = {}
        self.q_satctr = {}
        self.q_lastctr = {}
        self.q_dsatctr = {}

        last_action_time = -1
        last_click_time = -1
        last_action = ""
        last_click_url = -1
        last_click_query = -1
        query_clicks = {}
        uniqq = set([])
        serp2query = {}
        url2pos = {}
        was_switch = False
        last_switch = False

        for action in session["actions"]:
            if action[1] != "S":
                last_switch = False
                self.action_seq += action[1]
                if last_action_time != -1:
                    self.pauses.append(action[0] - last_action_time)
                last_action_time = action[0]

                if last_action == "C":                    
                    self.dwells.append(self.pauses[-1])
                    if self.dwells[-1] > LONG_DWELL:
                        self.long_dwell_clicks += 1
                        self.extended_seq += "L"
                        self.q_satctr[last_click_query][0] += 1
                        self.qu_satctr[(last_click_query, last_click_url)][0] += 1
                    elif self.dwells[-1] < SHORT_DWELL:
                        self.short_dwell_clicks += 1
                        self.extended_seq += "S"
                        self.q_dsatctr[last_click_query][0] += 1
                        self.qu_dsatctr[(last_click_query, last_click_url)][0] += 1
                    else:
                        self.extended_seq += "C"
                    self.extended_seq2 += self.extended_seq[-1]
                elif last_action == "Q":
                    if self.pauses[-1] > LONG_DWELL:
                        self.extended_seq2 += "Q"
                    elif self.pauses[-1] < SHORT_DWELL:
                        self.extended_seq2 += "q"
                    else: self.extended_seq2 += "K"


                if action[1] == "Q":
                    self.extended_seq += "Q"
                    self.queries_count += 1
                    serp2query[action[2]] = action[3]
                    uniqq.add(action[3])
                    query_clicks[action[3]] = 0

                    if action[3] not in self.q_ctr:
                        self.q_ctr[action[3]] = [0, 0]
                        self.q_satctr[action[3]] = [0, 0]
                        self.q_dsatctr[action[3]] = [0, 0]
                        self.q_lastctr[action[3]] = [0, 0]
                        self.query_ave_click_pos[action[3]] = 0

                    self.q_ctr[action[3]][1] += 1
                    self.q_satctr[action[3]][1] += 1
                    self.q_dsatctr[action[3]][1] += 1
                    self.q_lastctr[action[3]][1] += 1

                    last_action = "Q"
                    if not was_switch:
                        self.query_right_before_switch = action[3]
                        self.queries_before_switch.add(action[3])
                        self.urls_right_before_switch.clear()
                        for url in action[4:]:
                            self.urls_right_before_switch.add(url)
                            self.urls_before_switch.add(url)

                    pos = 1
                    for url in action[4:]:
                        url2pos[url] = pos
                        if (action[3], url) not in self.qu_ctr:
                            self.qu_ctr[(action[3], url)] = [0, 0]
                            self.qu_satctr[(action[3], url)] = [0, 0]
                            self.qu_dsatctr[(action[3], url)] = [0, 0]
                            self.qu_lastctr[(action[3], url)] = [0, 0]
                        self.qu_ctr[(action[3], url)][1] += 1
                        self.qu_satctr[(action[3], url)][1] += 1
                        self.qu_dsatctr[(action[3], url)][1] += 1
                        self.qu_lastctr[(action[3], url)][1] += 1
                        pos += 1
                elif action[1] == "C":
                    if self.clicks_count == 0:
                        self.time_1click = action[0]
                    self.clicks_count += 1
                    query_clicks[serp2query[action[2]]] += 1

                    self.q_ctr[serp2query[action[2]]][0] += 1

                    self.qu_ctr[(serp2query[action[2]], action[3])][0] += 1

                    self.ave_click_pos += url2pos[action[3]]
                    self.query_ave_click_pos[serp2query[action[2]]] += url2pos[action[3]]
                    if last_click_time != -1:
                        self.time_between_clicks += action[0] - last_click_time
                    last_click_time = action[0]
                    last_action = "C"
                    last_click_query = serp2query[action[2]]
                    last_click_url = action[3]
            else:
                self.time_to_switch = action[0]
                was_switch = True
                last_switch = True

        if was_switch and last_switch:
            self.is_last_switch = 1

        self.duration = last_action_time
        if last_action == "Q":
            self.is_last_query = 1
            self.extended_seq2 += "Q"
        else:
            self.is_last_click = 1
            self.dwells.append(LAST_CLICK_DWELL)
            self.long_dwell_clicks += 1
            self.extended_seq += "L"
            self.extended_seq2 += "L"
            if not last_switch:
                action = session["actions"][-1]
                self.q_lastctr[serp2query[action[2]]][1] += 1
                self.qu_lastctr[(last_click_query, last_click_url)][0] += 1

        if len(self.dwells) > 0:
            self.ave_dwell = 1.0 * sum(self.dwells) / (len(self.dwells) + 1)
            self.min_dwell = min(self.dwells)
            self.max_dwell = max(self.dwells)

        if len(self.pauses) > 0:
            self.ave_pause = 1.0 * sum(self.pauses) / (len(self.pauses) + 1)
            self.min_pause = min(self.pauses)
            self.max_pause = max(self.pauses)

        self.actions_count = self.queries_count + self.clicks_count
        self.clicks_per_query = 1.0 * self.clicks_count / self.queries_count
        self.duration_per_query = 1.0 * self.duration / self.queries_count
        self.duration_per_action = 1.0 * self.duration / self.actions_count
        if self.clicks_count > 1:
            self.time_between_clicks /= 1.0 * (self.clicks_count - 1)

        for query in self.query_ave_click_pos:
            self.query_ave_click_pos[query] = [self.query_ave_click_pos[query], self.q_ctr[query][0]]

        self.ave_click_pos = 1.0 * self.ave_click_pos / self.clicks_count if self.clicks_count > 0 else 11.0

        self.unique_queries = len(uniqq)
        for query in query_clicks:            
            self.max_click_per_query = self.max_click_per_query if self.max_click_per_query > query_clicks[query] else query_clicks[query]
            if query_clicks[query] == 0:
                self.abandoned += 1

        # print session["switchtype"] + "\t" + self.action_seq + "\t" + self.extended_seq + "\t" + self.extended_seq2

class StatisticsCollector:
    def __init__(self, personalized):
        self.personalized = personalized

        self.SWITCH = 1
        self.NONSWITCH = 0

        self._mid_switch = 0
        self._last_switch = 0
        self._serp_switch = 0
        self._toolbar_switch = 0
        self._time_to_switch = 0

        self._switch_by_day = [0, ] * 7

        self._count = [0, 0]
        self._queries_count = [0, 0]
        self._clicks_count = [0, 0]
        self._actions_count = [0, 0]
        self._time_1click = [0, 0]
        self._abandoned = [0, 0]
        self._ave_dwell = [0, 0]
        self._max_dwell = [0, 0]
        self._std_dwell = [0, 0]
        self._min_dwell = [0, 0]
        self._clicks_per_query = [0, 0]
        self._duration = [0, 0]
        self._unique_queries = [0, 0]
        self._duration_per_query = [0, 0]
        self._duration_per_action = [0, 0]
        self._min_pause = [0, 0]
        self._ave_pause = [0, 0]
        self._std_pause = [0, 0]
        self._max_pause = [0, 0]
        self._ave_click_pos = [0, 0]
        self._max_click_per_query = [0, 0]
        self._long_dwell_clicks = [0, 0]
        self._short_dwell_clicks = [0, 0]
        self._time_between_clicks = [0, 0]
        self._is_last_click = [0, 0]
        self._is_last_query = [0, 0]
        self._action_seqs = [[], []]
        self._action_extended_seqs = [[], []]
        self._action_extended_seqs2 = [[], []]
        self._seq_count = [{}, {}]
        self._ext_seq_count = [{}, {}]

        self._ext_2grams = [{}, {}]
        self._ext_3grams = [{}, {}]
        self._ext_4grams = [{}, {}]

        self._ext_2grams2 = [{}, {}]
        self._ext_3grams2 = [{}, {}]
        self._ext_4grams2 = [{}, {}]

        self._qu_ctr = {}
        self._qu_satctr = {}
        self._qu_dsatctr = {}
        self._qu_lastctr = {}

        self._q_ctr = {}
        self._q_satctr = {}
        self._q_dsatctr = {}
        self._q_lastctr = {}

        self._query_ave_click_pos = {}

        self._seqProbs = None
        self._ext_seqProbs = None
        self._ext_seqProbs2 = None
        self._double_seq_probs = None
        self._double_ext_seq_probs = None
        self._double_ext_seq_probs2 = None

        self._queryid_count = [{}, {}]
        self._queryid_rightbefore_count = [{}, {}]
        self._urlid_count = [{}, {}]
        self._urlid_rightbefore_count = [{}, {}]

    def add_session(self, session_stats, switchtype):

        if switchtype != "N":
            if switchtype != "B":
                self._serp_switch += 1
            else:
                self._toolbar_switch += 1

            if session_stats.is_last_switch:
                self._last_switch += 1
            else:
                self._mid_switch += 1
            self._time_to_switch += session_stats.time_to_switch
            self._switch_by_day[session_stats.day % 7] += 1

        index = self.SWITCH if switchtype != "N" else self.NONSWITCH
        self._count[index] += 1
        self._queries_count[index] += session_stats.queries_count
        self._clicks_count[index] += session_stats.clicks_count
        self._actions_count[index] += session_stats.actions_count
        self._time_1click[index] += session_stats.time_1click
        self._abandoned[index] += session_stats.abandoned
        self._ave_dwell[index] += session_stats.ave_dwell
        self._std_dwell[index] += std(session_stats.dwells)
        self._max_dwell[index] += session_stats.max_dwell
        self._min_dwell[index] += session_stats.min_dwell
        self._clicks_per_query[index] += session_stats.clicks_per_query
        self._duration[index] += session_stats.duration
        self._unique_queries[index] += session_stats.unique_queries
        self._duration_per_query[index] += session_stats.duration_per_query
        self._duration_per_action[index] += session_stats.duration_per_action
        self._min_pause[index] += session_stats.min_pause
        self._ave_pause[index] += session_stats.ave_pause
        self._std_pause[index] += std(session_stats.pauses)
        self._max_pause[index] += session_stats.max_pause
        self._ave_click_pos[index] += session_stats.ave_click_pos
        self._max_click_per_query[index] += session_stats.max_click_per_query
        self._short_dwell_clicks[index] += session_stats.short_dwell_clicks
        self._long_dwell_clicks[index] += session_stats.long_dwell_clicks
        self._time_between_clicks[index] += session_stats.time_between_clicks
        self._is_last_query[index] += session_stats.is_last_query
        self._is_last_click[index] += session_stats.is_last_click
        self._action_seqs[index].append(session_stats.action_seq)
        self._action_extended_seqs[index].append(session_stats.extended_seq)
        self._action_extended_seqs2[index].append(session_stats.extended_seq2)
        
        if not self.personalized:
            for query in session_stats.q_ctr.iterkeys():
                if query not in query_filter: continue

                if query not in self._q_ctr:                
                    self._q_ctr[query] = [0, 0]
                    self._q_satctr[query] = [0, 0]
                    self._q_dsatctr[query] = [0, 0]
                    self._q_lastctr[query] = [0, 0]
                    self._query_ave_click_pos[query] = [0, 0]

                self._q_ctr[query][0] += session_stats.q_ctr[query][0]
                self._q_ctr[query][1] += session_stats.q_ctr[query][1]
                self._q_satctr[query][0] += session_stats.q_satctr[query][0]
                self._q_satctr[query][1] += session_stats.q_satctr[query][1]
                self._q_dsatctr[query][0] += session_stats.q_dsatctr[query][0]
                self._q_dsatctr[query][1] += session_stats.q_dsatctr[query][1]
                self._q_lastctr[query][0] += session_stats.q_lastctr[query][0]
                self._q_lastctr[query][1] += session_stats.q_lastctr[query][1]
                self._query_ave_click_pos[query][0] += session_stats.query_ave_click_pos[query][0]
                self._query_ave_click_pos[query][1] += session_stats.query_ave_click_pos[query][1]

            for qupair in session_stats.qu_ctr.iterkeys():
                query, url = qupair
                if query not in query_filter or url not in url_filter: continue
                if (query, url) not in self._qu_ctr:
                    self._qu_ctr[(query, url)] = [0, 0]
                    self._qu_satctr[(query, url)] = [0, 0]
                    self._qu_dsatctr[(query, url)] = [0, 0]
                    self._qu_lastctr[(query, url)] = [0, 0]
                self._qu_ctr[(query, url)][0] += session_stats.qu_ctr[(query, url)][0]
                self._qu_ctr[(query, url)][1] += session_stats.qu_ctr[(query, url)][1]
                self._qu_satctr[(query, url)][0] += session_stats.qu_satctr[(query, url)][0]
                self._qu_satctr[(query, url)][1] += session_stats.qu_satctr[(query, url)][1]
                self._qu_dsatctr[(query, url)][0] += session_stats.qu_dsatctr[(query, url)][0]
                self._qu_dsatctr[(query, url)][1] += session_stats.qu_dsatctr[(query, url)][1]
                self._qu_lastctr[(query, url)][0] += session_stats.qu_lastctr[(query, url)][0]
                self._qu_lastctr[(query, url)][1] += session_stats.qu_lastctr[(query, url)][1]
                
        if session_stats.action_seq not in self._seq_count[index]:
            self._seq_count[0][session_stats.action_seq] = 0
            self._seq_count[1][session_stats.action_seq] = 0
        self._seq_count[index][session_stats.action_seq] += 1

        if session_stats.extended_seq not in self._ext_seq_count[index]:
            self._ext_seq_count[0][session_stats.extended_seq] = 0
            self._ext_seq_count[1][session_stats.extended_seq] = 0
        self._ext_seq_count[index][session_stats.extended_seq] += 1

        # calculate n-grams
        for i in xrange(len(session_stats.extended_seq) - 1):
            if session_stats.extended_seq[i:i + 2] not in self._ext_2grams[0]:
                self._ext_2grams[0][session_stats.extended_seq[i:i + 2]] = 0
                self._ext_2grams[1][session_stats.extended_seq[i:i + 2]] = 0
            self._ext_2grams[index][session_stats.extended_seq[i:i + 2]] += 1

            if i < len(session_stats.extended_seq) - 2:
                if session_stats.extended_seq[i:i + 3] not in self._ext_3grams[0]:
                    self._ext_3grams[0][session_stats.extended_seq[i:i + 3]] = 0
                    self._ext_3grams[1][session_stats.extended_seq[i:i + 3]] = 0
                self._ext_3grams[index][session_stats.extended_seq[i:i + 3]] += 1

            if i < len(session_stats.extended_seq) - 3:
                if session_stats.extended_seq[i:i + 4] not in self._ext_4grams[0]:
                    self._ext_4grams[0][session_stats.extended_seq[i:i + 4]] = 0
                    self._ext_4grams[1][session_stats.extended_seq[i:i + 4]] = 0
                self._ext_4grams[index][session_stats.extended_seq[i:i + 4]] += 1

        for i in xrange(len(session_stats.extended_seq2) - 1):
            if session_stats.extended_seq2[i:i + 2] not in self._ext_2grams2[0]:
                self._ext_2grams2[0][session_stats.extended_seq2[i:i + 2]] = 0
                self._ext_2grams2[1][session_stats.extended_seq2[i:i + 2]] = 0
            self._ext_2grams2[index][session_stats.extended_seq2[i:i + 2]] += 1

            if i < len(session_stats.extended_seq2) - 2:
                if session_stats.extended_seq2[i:i + 3] not in self._ext_3grams2[0]:
                    self._ext_3grams2[0][session_stats.extended_seq2[i:i + 3]] = 0
                    self._ext_3grams2[1][session_stats.extended_seq2[i:i + 3]] = 0
                self._ext_3grams2[index][session_stats.extended_seq2[i:i + 3]] += 1

            if i < len(session_stats.extended_seq2) - 3:
                if session_stats.extended_seq2[i:i + 4] not in self._ext_4grams2[0]:
                    self._ext_4grams2[0][session_stats.extended_seq2[i:i + 4]] = 0
                    self._ext_4grams2[1][session_stats.extended_seq2[i:i + 4]] = 0
                self._ext_4grams2[index][session_stats.extended_seq2[i:i + 4]] += 1

        for query in session_stats.queries_before_switch:
            if query not in query_filter: continue
            if query not in self._queryid_count[index]:
                self._queryid_count[index][query] = 0
                self._queryid_rightbefore_count[index][query] = 0
            self._queryid_count[index][query] += 1

        for url in session_stats.urls_before_switch:
            if url not in url_filter: continue
            if url not in self._urlid_count[index]:
                self._urlid_count[index][url] = 0
                self._urlid_rightbefore_count[index][url] = 0
            self._urlid_count[index][url] += 1


    def norm(self, value, switch):
        ret = 1.0 * value[switch] / (self._count[switch] + 1)
        if ret == 0:
            return EPS
        return ret

    def _construct_transitions(self, seqProbs, action_seqs):
        total = {}
        for seq in action_seqs:
            last_action = seq[0]
            for action in seq[1:]:
                if last_action not in total:
                    total[last_action] = 0
                total[last_action] += 1
                if (last_action + action) not in seqProbs:
                    seqProbs[last_action + action] = 0
                seqProbs[last_action + action] += 1
                last_action = action
        actionscount = len(total.keys())
        for actionpair in seqProbs.iterkeys():
            seqProbs[actionpair] = 1.0 * (seqProbs[actionpair] + 1) / (total[actionpair[0]] + actionscount)

    def _construct_double_transitions(self, seqProbs, action_seqs):
        total = {}
        for seq in action_seqs:
            if len(seq) < 3: continue
            last_actions = seq[0:2]
            for action in seq[2:]:
                if last_actions not in total:
                    total[last_actions] = 0
                total[last_actions] += 1
                if (last_actions + action) not in seqProbs:
                    seqProbs[last_actions + action] = 0
                seqProbs[last_actions + action] += 1
                last_actions = last_actions[1] + action
        actionscount = len(total.keys())
        for actionpair in seqProbs.iterkeys():
            seqProbs[actionpair] = 1.0 * (seqProbs[actionpair] + 1) / (total[actionpair[0:2]] + actionscount)       

    def get_seq_prob(self, sequence, extended_seq, extended_seq2, switch, prefix, featurenames):
        if self._seqProbs == None:
            self._seqProbs = [{}, {}]
            self._construct_transitions(self._seqProbs[0], self._action_seqs[0])
            self._construct_transitions(self._seqProbs[1], self._action_seqs[1])

        if self._ext_seqProbs == None:
            self._ext_seqProbs = [{}, {}]
            self._construct_transitions(self._ext_seqProbs[0], self._action_extended_seqs[0])
            self._construct_transitions(self._ext_seqProbs[1], self._action_extended_seqs[1])

        if self._ext_seqProbs2 == None:
            self._ext_seqProbs2 = [{}, {}]
            self._construct_transitions(self._ext_seqProbs2[0], self._action_extended_seqs2[0])
            self._construct_transitions(self._ext_seqProbs2[1], self._action_extended_seqs2[1])


        if self._double_seq_probs == None:
            self._double_seq_probs = [{}, {}]
            self._construct_double_transitions(self._double_seq_probs[0], self._action_seqs[0])
            self._construct_double_transitions(self._double_seq_probs[1], self._action_seqs[1])

        if self._double_ext_seq_probs == None:
            self._double_ext_seq_probs = [{}, {}]
            self._construct_double_transitions(self._double_ext_seq_probs[0], self._action_extended_seqs[0])
            self._construct_double_transitions(self._double_ext_seq_probs[1], self._action_extended_seqs[1])

        if self._double_ext_seq_probs2 == None:
            self._double_ext_seq_probs2 = [{}, {}]
            self._construct_double_transitions(self._double_ext_seq_probs2[0], self._action_extended_seqs2[0])
            self._construct_double_transitions(self._double_ext_seq_probs2[1], self._action_extended_seqs2[1])

        res1 = 1.0
        last_action = sequence[0]
        for action in sequence[1:]:            
            res1 *= self._seqProbs[switch][last_action + action] if last_action + action in self._seqProbs[switch] else 1.0
            last_action = action

        res2 = 1.0
        last_action = extended_seq[0]
        for action in extended_seq[1:]:
            res2 *= self._ext_seqProbs[switch][last_action + action] if last_action + action in self._ext_seqProbs[switch] else 1.0
            last_action = action

        res7 = 1.0
        last_action = extended_seq2[0]
        for action in extended_seq2[1:]:
            res7 *= self._ext_seqProbs2[switch][last_action + action] if last_action + action in self._ext_seqProbs2[switch] else 1.0
            last_action = action

        res3 = 1.0
        if len(sequence) > 2:
            last_actions = sequence[0:2]
            for action in sequence[2:]:
                res3 *= self._double_seq_probs[switch][last_actions + action] if last_actions + action in self._double_seq_probs[switch] else 1.0
                last_actions = last_actions[1] + action

        res4 = 1.0
        if len(extended_seq) > 2:
            last_actions = extended_seq[0:2]
            for action in extended_seq[2:]:
                res4 *= self._double_ext_seq_probs[switch][last_actions + action] if last_actions + action in self._double_ext_seq_probs[switch] else 1.0
                last_actions = last_actions[1] + action

        res8 = 1.0
        if len(extended_seq2) > 2:
            last_actions = extended_seq2[0:2]
            for action in extended_seq2[2:]:
                res8 *= self._double_ext_seq_probs2[switch][last_actions + action] if last_actions + action in self._double_ext_seq_probs2[switch] else 1.0
                last_actions = last_actions[1] + action

        res5 = 0.0
        if sequence in self._seq_count[switch]:
            res5 = 1.0 * (self._seq_count[switch][sequence] + 1) / (self._seq_count[switch][sequence] + self._seq_count[not switch][sequence] + 20)

        res6 = 0.0
        if extended_seq in self._ext_seq_count[switch]:
            res6 = 1.0 * (self._ext_seq_count[switch][extended_seq] + 1) / (self._ext_seq_count[switch][extended_seq] + self._ext_seq_count[not switch][extended_seq] + 20)

        res10 = 0.0
        res11 = 0.0
        res12 = 0.0
        for i in xrange(len(extended_seq) - 1):
            freq1 = self._ext_2grams[switch][extended_seq[i:i+2]] if extended_seq[i:i+2] in self._ext_2grams[switch] else 0
            freq2 = self._ext_2grams[not switch][extended_seq[i:i+2]] if extended_seq[i:i+2] in self._ext_2grams[not switch] else 0
            res10 += 1.0 / (len(extended_seq)) * (freq1 + 1.0) / (freq2 + 1.0)

            if i < len(extended_seq) - 2:
                freq1 = self._ext_3grams[switch][extended_seq[i:i+3]] if extended_seq[i:i+3] in self._ext_3grams[switch] else 0
                freq2 = self._ext_3grams[not switch][extended_seq[i:i+3]] if extended_seq[i:i+3] in self._ext_3grams[not switch] else 0
                res11 += 1.0 / (len(extended_seq)) * (freq1 + 1.0) / (freq2 + 1.0)

            if i < len(extended_seq) - 3:
                freq1 = self._ext_4grams[switch][extended_seq[i:i+4]] if extended_seq[i:i+4] in self._ext_4grams[switch] else 0
                freq2 = self._ext_4grams[not switch][extended_seq[i:i+4]] if extended_seq[i:i+4] in self._ext_4grams[not switch] else 0
                res12 += 1.0 / (len(extended_seq)) * (freq1 + 1.0) / (freq2 + 1.0)

        res13 = 0.0
        res14 = 0.0
        res15 = 0.0
        for i in xrange(len(extended_seq2) - 1):
            freq1 = self._ext_2grams2[switch][extended_seq2[i:i+2]] if extended_seq2[i:i+2] in self._ext_2grams2[switch] else 0
            freq2 = self._ext_2grams2[not switch][extended_seq2[i:i+2]] if extended_seq2[i:i+2] in self._ext_2grams2[not switch] else 0
            res13 += 1.0 / (len(extended_seq2)) * (freq1 + 1.0) / (freq2 + 1.0)

            if i < len(extended_seq2) - 2:
                freq1 = self._ext_3grams2[switch][extended_seq2[i:i+3]] if extended_seq2[i:i+3] in self._ext_3grams2[switch] else 0
                freq2 = self._ext_3grams2[not switch][extended_seq2[i:i+3]] if extended_seq2[i:i+3] in self._ext_3grams2[not switch] else 0
                res14 += 1.0 / (len(extended_seq)) * (freq1 + 1.0) / (freq2 + 1.0)

            if i < len(extended_seq2) - 3:
                freq1 = self._ext_4grams2[switch][extended_seq2[i:i+4]] if extended_seq2[i:i+4] in self._ext_4grams2[switch] else 0
                freq2 = self._ext_4grams2[not switch][extended_seq2[i:i+4]] if extended_seq2[i:i+4] in self._ext_4grams2[not switch] else 0
                res15 += 1.0 / (len(extended_seq)) * (freq1 + 1.0) / (freq2 + 1.0)

        featurenames += [prefix + "markovmodel", prefix + "markovmodel_ext", prefix + "double_markovmodel", prefix + "double_markovmodel_ext", prefix + "sequence_prob", prefix + "ext_sequence_prob", prefix + "markovmodel_ext2", prefix + "double_markovmodel_ext2",]
        featurenames += [prefix + "seq_ave_2grams_freq", prefix + "seq_ave_3grams_freq", prefix + "seq_ave_4grams_freq", prefix + "seq2_ave_2grams_freq", prefix + "seq2_ave_3grams_freq", prefix + "seq2_ave_4grams_freq", ]

        return [res1, res2, res3, res4, res5, res6, res7, res8, res10, res11, res12, res13, res14, res15]

    def get_query_features(self, session_stat, prefix, featurenames):
        q_ctrs1 = []
        q_ctrs2 = []
        q_satctrs1 = []
        q_satctrs2 = []
        q_dsatctrs1 = []
        q_dsatctrs2 = []
        q_lastctrs1 = []
        q_lastctrs2 = []        
        q_ave_click_pos = []
        q_freq = []
        for query in session_stat.queries_before_switch:
            if query in self._q_ctr:
                q_ctrs1.append(1.0  * (self._q_ctr[query][0] + 1) / (self._q_ctr[query][1] + 10))
                q_ctrs2.append(1.0  * (self._q_ctr[query][0] + 1) / (self._q_ctr[query][1] + 100))
                q_satctrs1.append(1.0  * (self._q_satctr[query][0] + 1) / (self._q_satctr[query][1] + 10))
                q_satctrs2.append(1.0  * (self._q_satctr[query][0] + 1) / (self._q_satctr[query][1] + 100))
                q_dsatctrs1.append(1.0  * (self._q_dsatctr[query][0] + 1) / (self._q_dsatctr[query][1] + 10))
                q_dsatctrs2.append(1.0  * (self._q_dsatctr[query][0] + 1) / (self._q_dsatctr[query][1] + 100))                
                q_lastctrs1.append(1.0  * (self._q_lastctr[query][0] + 1) / (self._q_lastctr[query][1] + 10))
                q_lastctrs2.append(1.0  * (self._q_lastctr[query][0] + 1) / (self._q_lastctr[query][1] + 100))    
                q_ave_click_pos.append(1.0 * (self._query_ave_click_pos[query][0] + 1) / (self._query_ave_click_pos[query][1] + 1))
                q_freq.append(1.0 * self._q_ctr[query][1] / (self._count[0] + self._count[1]))

        res_feats = []
        for switch in [0, 1]:
            res = []
            for query in session_stat.queries_before_switch:            
                if query in self._queryid_count[switch]:
                    res.append(1.0 * (self._queryid_count[switch][query] + 1) / (self._queryid_count[switch][query] + (self._queryid_count[not switch][query] if query in self._queryid_count[not switch] else 0) + 100))
            if len(res) < 2: res = [0.01,0.01]
            res.sort()

            res2 = 0.01
            query = session_stat.query_right_before_switch
            if query != -1 and query in self._queryid_rightbefore_count[switch]:
                res2 = 1.0 * (self._queryid_rightbefore_count[switch][query] + 1) / (self._queryid_rightbefore_count[switch][query] + (self._queryid_rightbefore_count[not switch][query] if query in self._queryid_rightbefore_count[not switch] else 0) + 100)

            res_feats += [mean(res), std(res), res[0], res[-1], res[-2], res2, ]

        featurenames += [prefix + "ave_query_nonswitchprob", prefix + "std_query_nonswitchprob", prefix + "min_query_nonswitchprob", prefix + "max_query_nonswitchprob", prefix + "secondmax_query_nonswitchprob", prefix + "lastinsession_query_prob",]
        featurenames += [prefix + "ave_query_switchprob", prefix + "std_query_switchprob", prefix + "min_query_switchprob", prefix + "max_query_switchprob", prefix + "secondmax_query_switchprob", prefix + "ave_query_rightbefore_switchprob",]

        if len(q_ctrs1) == 0:
            q_ctrs1 = [0, ]
            q_ctrs2 = [0, ]
            q_satctrs1 = [0, ]
            q_satctrs2 = [0, ]
            q_dsatctrs1 = [0, ]
            q_dsatctrs2 = [0, ]
            q_lastctrs1 = [0, ]
            q_lastctrs2 = [0, ]
            q_ave_click_pos = [11, ]
            q_freq = [0, ]

        featurenames += [prefix + "ave_qctr_smooth10", prefix + "max_qctr_smooth10",  prefix + "ave_qctr_smooth100", prefix + "max_qctr_smooth100", prefix + "ave_qsatctr_smooth10", prefix + "max_qsatctr_smooth10",  prefix + "ave_qsatctr_smooth100", prefix + "max_qsatctr_smooth100", ]
        featurenames += [prefix + "ave_qdsatctr_smooth10", prefix + "max_qdsatctr_smooth10",  prefix + "ave_qdsatctr_smooth100", prefix + "max_qdsatctr_smooth100", prefix + "ave_qlastctr_smooth10", prefix + "max_qlastctr_smooth10",  prefix + "ave_qlastctr_smooth100", prefix + "max_qlastctr_smooth100",]
        featurenames += [prefix + "average_query_clickpos", prefix + "max_query_clickpos", prefix + "min_query_clickpos", prefix + "average_query_frequency", prefix + "max_query_frequency"]

        return res_feats + [mean(q_ctrs1), max(q_ctrs1), mean(q_ctrs2), max(q_ctrs2), mean(q_satctrs1), max(q_satctrs1), mean(q_satctrs2), max(q_satctrs2),mean(q_dsatctrs1), max(q_dsatctrs1), mean(q_dsatctrs2), max(q_dsatctrs2), mean(q_lastctrs1), max(q_lastctrs1), mean(q_lastctrs2), max(q_lastctrs2), mean(q_ave_click_pos), max(q_ave_click_pos), min(q_freq), mean(q_freq), max(q_freq)]

    def get_url_features(self, session_stat, prefix, featurenames):
        res_feats = []

        ctrs = []
        satctrs = []
        dsatctrs = []
        lastctrs = []
        for qupair in session_stat.q_ctr.iterkeys():
            if qupair in self._q_ctr:
                ctrs.append(1.0 * (self._q_ctr[qupair][0] + 1) / (self._q_ctr[qupair][0] + 100))
            if qupair in self._q_satctr:
                satctrs.append(1.0 * (self._q_satctr[qupair][0] + 1) / (self._q_satctr[qupair][1] + 100))
            if qupair in self._q_dsatctr:
                dsatctrs.append(1.0 * (self._q_dsatctr[qupair][0] + 1) / (self._q_dsatctr[qupair][1] + 100))
            if qupair in self._q_lastctr:
                lastctrs.append(1.0 * (self._q_lastctr[qupair][0] + 1) / (self._q_lastctr[qupair][1] + 100))

        if len(ctrs) == 0:
            ctrs.append(0)
        if len(satctrs) == 0:
            satctrs.append(0)
        if len(dsatctrs) == 0:
            dsatctrs.append(0)
        if len(lastctrs) == 0:
            lastctrs.append(0)

        res_feats += [mean(ctrs), max(ctrs), min(ctrs), mean(satctrs), max(satctrs), min(satctrs), mean(dsatctrs), max(dsatctrs), min(dsatctrs),mean(lastctrs), max(lastctrs), min(lastctrs),]
        featurenames += [prefix + "ave_clicked_doc_ctrs", prefix + "max_clicked_doc_ctr", prefix + "min_clicked_doc_ctr", prefix + "ave_clicked_doc_satctrs", prefix + "max_clicked_doc_satctr", prefix + "min_clicked_doc_satctr", prefix + "ave_clicked_doc_dsatctrs", prefix + "max_clicked_doc_dsatctr", prefix + "min_clicked_doc_dsatctr", prefix + "ave_clicked_doc_lastctrs", prefix + "max_clicked_doc_lastctr", prefix + "min_clicked_doc_lastctr",]

        for switch in [0, 1]:
            res = []
            for url in session_stat.urls_before_switch:
                if url in self._urlid_count[switch]:
                    res.append(1.0 * (self._urlid_count[switch][url] + 1) / (self._urlid_count[switch][url] + (self._urlid_count[not switch][url] if url in self._urlid_count[not switch] else 0) + 100))
            if len(res) < 2: res = [0, 0]
            res.sort()
            res2 = []
            for url in session_stat.urls_right_before_switch:
                if url in self._urlid_rightbefore_count[switch]:
                    res2.append(1.0 * (self._urlid_rightbefore_count[switch][url] + 1) / (self._urlid_rightbefore_count[switch][url] + (self._urlid_rightbefore_count[not switch][url] if url in self._urlid_rightbefore_count[not switch] else 0) + 100))
            if len(res2) < 2: res2 = [0, 0]
            res2.sort()
            res_feats += [mean(res), res[0], res[-1], res[-2], std(res), mean(res2), res2[0], res2[-1], res2[-2], std(res2)]

        featurenames += [prefix + "ave_clickedurl_nonswitchprob", prefix + "min_clickedurl_nonswitchprob", prefix + "max_clickedurl_nonswitchprob", prefix + "secondmax_clickedurl_nonswitchprob", prefix + "std_clickedurl_nonswitchprob", ]
        featurenames += [prefix + "ave_clickedurl_nonswitchprob_rightbefore", prefix + "min_clickedurl_nonswitchprob_rightbefore", prefix + "max_clickedurl_nonswitchprob_rightbefore", prefix + "secondmax_clickedurl_nonswitchprob_rightbefore", prefix + "std_clickedurl_nonswitchprob_rightbefore",]
        featurenames += [prefix + "ave_clickedurl_switchprob", prefix + "min_clickedurl_switchprob", prefix + "max_clickedurl_switchprob", prefix + "secondmax_clickedurl_switchprob", prefix + "std_clickedurl_switchprob", ]
        featurenames += [prefix + "ave_clickedurl_switchprob_rightbefore", prefix + "min_clickedurl_switchprob_rightbefore", prefix + "max_clickedurl_switchprob_rightbefore", prefix + "secondmax_clickedurl_switchprob_rightbefore", prefix + "std_clickedurl_switchprob_rightbefore",]
        return res_feats


class FeatureCalculator:
    def __init__(self):
        self._overal_stats = StatisticsCollector(False)
        self._user_stats = {}

    def processSessions(self, inputstream, is_train, callback):
        for sessionid, data in groupby(inputstream, lambda x : x.strip().split("\t")[0]):
            session = {"id" : int(sessionid), "day" : -1, "switchtype" : False, "user" : -1, "actions" : []}
            for line in data:
                line = line.strip().split("\t")
                if line[2] == "M":
                    session["user"] = int(line[3])
                    session["day"] = int(line[1])
                    session["switchtype"] = line[4] if len(line) > 4 else "N"
                elif line[2] == "Q":
                    session["actions"].append([int(line[i]) if i != 2 else line[i] for i in xrange(1, len(line))])
                elif line[2] == "C":
                    session["actions"].append([int(line[1]), line[2], int(line[3]), int(line[4])] + map(int, line[5:]))
                elif line[2] == "S" and not is_train:
                    session["actions"].append([int(line[1]), line[2]])
            callback(session)

    def _session_stats_callback(self, session):
        session_stats = SessionStats(session)
        if session["user"] in user_filter:
            if session["user"] not in self._user_stats:
                self._user_stats[session["user"]] = StatisticsCollector(True)
            self._user_stats[session["user"]].add_session(session_stats, session["switchtype"])
        self._overal_stats.add_session(session_stats, session["switchtype"])

    def _filters_callback(self, session):
        user_filter.add(session["user"])
        for action in session["actions"]:
            if action[1] == "Q":
                query_filter.add(action[3])
                for url in action[4:]:
                    url_filter.add(url)

    def build_filters(self, inputstream):
        self.processSessions(inputstream, True, self._filters_callback)

    def collect_stats(self, inputstream):
        self.processSessions(inputstream, False, self._session_stats_callback)

    def norm_feats(self, session_stats, stats, special, prefix, featurenames):
        features = []
        if special:
            features += [stats._count[0] + stats._count[1], stats._count[1], 1.0 * stats._last_switch / (stats._count[0] + stats._count[1] + 1), 1.0 * stats._mid_switch / (stats._count[0] + stats._count[1] + 1), 1.0 * stats._serp_switch / (stats._count[0] + stats._count[1] + 1), 1.0 * stats._toolbar_switch / (stats._count[0] + stats._count[1] + 1)]
            featurenames += [prefix + "sessions_count", prefix + "switches_count", prefix + "frequency_of_last_switches", prefix + "frequency_of_mid_switches", prefix + "frequency_of_serp_switches", prefix + "frequency_of_toolbatswitches"]
            features += [1.0 * stats._time_to_switch / (stats._count[1] + 1)]
            featurenames += ["ave_time_to_switch"]
            features += [1.0 * stats._switch_by_day[0] / (stats._count[1] + 1), 1.0 * stats._switch_by_day[1] / (stats._count[1] + 1), 1.0 * stats._switch_by_day[2] / (stats._count[1] + 1), 1.0 * stats._switch_by_day[3] / (stats._count[1] + 1), 1.0 * stats._switch_by_day[4] / (stats._count[1] + 1), 1.0 * stats._switch_by_day[5] / (stats._count[1] + 1), 1.0 * stats._switch_by_day[6] / (stats._count[1] + 1), ]
            featurenames += [prefix + "weekday0_switchfreq", prefix + "weekday1_switchfreq", prefix + "weekday2_switchfreq", prefix + "weekday3_switchfreq", prefix + "weekday4_switchfreq", prefix + "weekday5_switchfreq", prefix + "weekday6_switchfreq",]
        
            features += [stats.norm(stats._queries_count, False), stats.norm(stats._queries_count, True)]
            featurenames += [prefix + "ave_query_count_in_nonswitch_sessions", prefix + "ave_query_count_in_switch_sessions"]
            features += [stats.norm(stats._clicks_count, False), stats.norm(stats._clicks_count, True)]
            featurenames += [prefix + "ave_click_count_in_nonswitch_sessions", prefix + "ave_click_count_in_switch_sessions"]            
            features += [stats.norm(stats._actions_count, False), stats.norm(stats._actions_count, True)]
            featurenames += [prefix + "ave_actions_count_in_nonswitch_sessions", prefix + "ave_actions_count_in_switch_sessions"]            
            features += [stats.norm(stats._time_1click, False), stats.norm(stats._time_1click, True)]
            featurenames += [prefix + "ave_time1click_in_nonswitch_sessions", prefix + "ave_time1click_in_switch_sessions"]            
            features += [stats.norm(stats._abandoned, False), stats.norm(stats._abandoned, True)]
            featurenames += [prefix + "ave_abandoned_query_count_in_nonswitch_sessions", prefix + "ave_abandoned_query_count_in_switch_sessions"]            
            features += [stats.norm(stats._ave_dwell, False), stats.norm(stats._ave_dwell, True)]
            featurenames += [prefix + "ave_dwell_in_nonswitch_sessions", prefix + "ave_dwell_in_switch_sessions"]            
            features += [stats.norm(stats._std_dwell, False), stats.norm(stats._std_dwell, True)]
            featurenames += [prefix + "ave_std_dwell_in_nonswitch_sessions", prefix + "ave_std_dwell_in_switch_sessions"]                        
            features += [stats.norm(stats._max_dwell, False), stats.norm(stats._max_dwell, True)]
            featurenames += [prefix + "ave_max_dwell_in_nonswitch_sessions", prefix + "ave_max_dwell_in_switch_sessions"]
            features += [stats.norm(stats._min_dwell, False), stats.norm(stats._min_dwell, True)]
            featurenames += [prefix + "ave_min_dwell_in_nonswitch_sessions", prefix + "ave_min_dwell_in_switch_sessions"]
            features += [stats.norm(stats._clicks_per_query, False), stats.norm(stats._clicks_per_query, True)]
            featurenames += [prefix + "ave_clicksperquery_in_nonswitch_sessions", prefix + "ave_clicksperquery_in_switch_sessions"]
            features += [stats.norm(stats._duration, False), stats.norm(stats._duration, True)]
            featurenames += [prefix + "ave_duration_in_nonswitch_sessions", prefix + "ave_duration_in_switch_sessions"]            
            features += [stats.norm(stats._unique_queries, False), stats.norm(stats._unique_queries, True)]
            featurenames += [prefix + "ave_unique_queries_in_nonswitch_sessions", prefix + "ave_unique_queries_in_switch_sessions"]            
            features += [stats.norm(stats._duration_per_query, False), stats.norm(stats._duration_per_query, True)]
            featurenames += [prefix + "ave_durationperquery_in_nonswitch_sessions", prefix + "ave_durationperquery_in_switch_sessions"]
            features += [stats.norm(stats._duration_per_action, False), stats.norm(stats._duration_per_action, True)]
            featurenames += [prefix + "ave_durationperaction_in_nonswitch_sessions", prefix + "ave_durationperaction_in_switch_sessions"]
            features += [stats.norm(stats._min_pause, False), stats.norm(stats._min_pause, True)]
            featurenames += [prefix + "ave_minpause_in_nonswitch_sessions", prefix + "ave_minpause_in_switch_sessions"]
            features += [stats.norm(stats._ave_pause, False), stats.norm(stats._ave_pause, True)]
            featurenames += [prefix + "ave_avepause_in_nonswitch_sessions", prefix + "ave_avepause_in_switch_sessions"]            
            features += [stats.norm(stats._std_pause, False), stats.norm(stats._std_pause, True)]
            featurenames += [prefix + "ave_stdpause_in_nonswitch_sessions", prefix + "ave_stdpause_in_switch_sessions"]            
            features += [stats.norm(stats._max_pause, False), stats.norm(stats._max_pause, True)]
            featurenames += [prefix + "ave_maxpause_in_nonswitch_sessions", prefix + "ave_maxpause_in_switch_sessions"]            
            features += [stats.norm(stats._ave_click_pos, False), stats.norm(stats._ave_click_pos, True)]
            featurenames += [prefix + "ave_clickpos_in_nonswitch_sessions", prefix + "ave_clickpos_in_switch_sessions"]            
            features += [stats.norm(stats._max_click_per_query, False), stats.norm(stats._max_click_per_query, True)]
            featurenames += [prefix + "ave_maxcxlicksperquery_in_nonswitch_sessions", prefix + "ave_maxcxlicksperquery_in_switch_sessions"]            
            features += [stats.norm(stats._short_dwell_clicks, False), stats.norm(stats._short_dwell_clicks, True)]
            featurenames += [prefix + "ave_shortdwellclicks_in_nonswitch_sessions", prefix + "ave_shortdwellclicks_in_switch_sessions"]
            features += [stats.norm(stats._long_dwell_clicks, False), stats.norm(stats._long_dwell_clicks, True)]
            featurenames += [prefix + "ave_longdwellclicks_in_nonswitch_sessions", prefix + "ave_longdwellclicks_in_switch_sessions"]            
            features += [stats.norm(stats._time_between_clicks, False), stats.norm(stats._time_between_clicks, True)]
            featurenames += [prefix + "ave_timebetweenclicks_in_nonswitch_sessions", prefix + "ave_timebetweenclicks_in_switch_sessions"]                        
            features += [stats.norm(stats._is_last_click, False), stats.norm(stats._is_last_click, True)]
            featurenames += [prefix + "ave_islastclick_in_nonswitch_sessions", prefix + "ave_islastclick_in_switch_sessions"]                        
            features += [stats.norm(stats._is_last_query, False), stats.norm(stats._is_last_query, True)]
            featurenames += [prefix + "ave_islastquery_in_nonswitch_sessions", prefix + "ave_islastquery_in_switch_sessions"]

        features += [1.0 * session_stats.queries_count / stats.norm(stats._queries_count, False), 1.0 * session_stats.queries_count / stats.norm(stats._queries_count, True)]
        featurenames += [prefix + "queries/ave_queriescount_in_nonswitch_sessions", prefix + "queries/ave_queriescount_in_switch_sessions"]
        features += [1.0 * session_stats.clicks_count / stats.norm(stats._clicks_count, False), 1.0 * session_stats.clicks_count / stats.norm(stats._clicks_count, True)]
        featurenames += [prefix + "clicks/ave_clickscount_in_nonswitch_sessions", prefix + "clicks/ave_clickscount_in_switch_sessions"]
        features += [1.0 * session_stats.actions_count / stats.norm(stats._actions_count, False), 1.0 * session_stats.actions_count / stats.norm(stats._actions_count, True)]
        featurenames += [prefix + "actions/ave_actionscount_in_nonswitch_sessions", prefix + "actions/ave_actionscount_in_switch_sessions"]
        features += [1.0 * session_stats.time_1click / stats.norm(stats._time_1click, False), 1.0 * session_stats.time_1click / stats.norm(stats._time_1click, True)]
        featurenames += [prefix + "time1click/ave_time1click_in_nonswitch_sessions", prefix + "time1click/ave_time1click_in_switch_sessions"]        
        features += [1.0 * session_stats.abandoned / stats.norm(stats._abandoned, False), 1.0 * session_stats.abandoned / stats.norm(stats._abandoned, True)]
        featurenames += [prefix + "abandoned/ave_abandoned_in_nonswitch_sessions", prefix + "abandoned/ave_abandoned_in_switch_sessions"]                
        features += [1.0 * session_stats.ave_dwell / stats.norm(stats._ave_dwell, False), 1.0 * session_stats.ave_dwell / stats.norm(stats._ave_dwell, True)]
        featurenames += [prefix + "avedwell/ave_avedwell_in_nonswitch_sessions", prefix + "avedwell/ave_avedwell_in_switch_sessions"]
        features += [1.0 * session_stats.max_dwell / stats.norm(stats._max_dwell, False), 1.0 * session_stats.max_dwell / stats.norm(stats._max_dwell, True)]
        featurenames += [prefix + "maxdwell/ave_maxdwell_in_nonswitch_sessions", prefix + "maxdwell/ave_maxdwell_in_switch_sessions"]        
        features += [1.0 * session_stats.min_dwell / stats.norm(stats._min_dwell, False), 1.0 * session_stats.min_dwell / stats.norm(stats._min_dwell, True)]
        featurenames += [prefix + "mindwell/ave_mindwell_in_nonswitch_sessions", prefix + "mindwell/ave_mindwell_in_switch_sessions"]
        features += [1.0 * session_stats.clicks_per_query / stats.norm(stats._clicks_per_query, False), 1.0 * session_stats.clicks_per_query / stats.norm(stats._clicks_per_query, True)]
        featurenames += [prefix + "clicksperquery/ave_clicksperquery_in_nonswitch_sessions", prefix + "clicksperquery/ave_clicksperquery_in_switch_sessions"]        
        features += [1.0 * session_stats.duration / stats.norm(stats._duration, False), 1.0 * session_stats.duration / stats.norm(stats._duration, True)]
        featurenames += [prefix + "duration/ave_duration_in_nonswitch_sessions", prefix + "duration/ave_duration_in_switch_sessions"]                
        features += [1.0 * session_stats.unique_queries / stats.norm(stats._unique_queries, False), 1.0 * session_stats.unique_queries / stats.norm(stats._unique_queries, True)]
        featurenames += [prefix + "unique_queries/ave_unique_queries_in_nonswitch_sessions", prefix + "unique_queries/ave_unique_queries_in_switch_sessions"]                        
        features += [1.0 * session_stats.duration_per_query / stats.norm(stats._duration_per_query, False), 1.0 * session_stats.duration_per_query / stats.norm(stats._duration_per_query, True)]
        featurenames += [prefix + "durationperquery/ave_durationperquery_in_nonswitch_sessions", prefix + "durationperquery/ave_durationperquery_in_switch_sessions"]
        features += [1.0 * session_stats.duration_per_action / stats.norm(stats._duration_per_action, False), 1.0 * session_stats.duration_per_action / stats.norm(stats._duration_per_action, True)]
        featurenames += [prefix + "durationperaction/ave_durationperaction_in_nonswitch_sessions", prefix + "durationperaction/ave_durationperaction_in_switch_sessions"]
        features += [1.0 * session_stats.min_pause / stats.norm(stats._min_pause, False), 1.0 * session_stats.min_pause / stats.norm(stats._min_pause, True)]
        featurenames += [prefix + "minpause/ave_minpause_in_nonswitch_sessions", prefix + "minpause/ave_minpause_in_switch_sessions"]
        features += [1.0 * session_stats.ave_pause / stats.norm(stats._ave_pause, False), 1.0 * session_stats.ave_pause / stats.norm(stats._ave_pause, True)]
        featurenames += [prefix + "avepause/ave_avepause_in_nonswitch_sessions", prefix + "avepause/ave_avepause_in_switch_sessions"]
        features += [1.0 * session_stats.max_pause / stats.norm(stats._max_pause, False), 1.0 * session_stats.max_pause / stats.norm(stats._max_pause, True)]
        featurenames += [prefix + "maxpause/ave_maxpause_in_nonswitch_sessions", prefix + "maxpause/ave_maxpause_in_switch_sessions"]        
        features += [1.0 * session_stats.ave_click_pos / stats.norm(stats._ave_click_pos, False), 1.0 * session_stats.ave_click_pos / stats.norm(stats._ave_click_pos, True)]
        featurenames += [prefix + "aveclickpos/ave_aveclickpos_in_nonswitch_sessions", prefix + "aveclickpos/ave_aveclickpos_in_switch_sessions"]                
        features += [1.0 * session_stats.max_click_per_query / stats.norm(stats._max_click_per_query, False), 1.0 * session_stats.max_click_per_query / stats.norm(stats._max_click_per_query, True)]
        featurenames += [prefix + "maxclickperquery/ave_maxclickperquery_in_nonswitch_sessions", prefix + "maxclickperquery/ave_maxclickperquery_in_switch_sessions"]
        features += [1.0 * session_stats.short_dwell_clicks / stats.norm(stats._short_dwell_clicks, False), 1.0 * session_stats.short_dwell_clicks / stats.norm(stats._short_dwell_clicks, True)]
        featurenames += [prefix + "shortdwellclicks/ave_shortdwellclicks_in_nonswitch_sessions", prefix + "shortdwellclicks/ave_shortdwellclicks_in_switch_sessions"]        
        features += [1.0 * session_stats.long_dwell_clicks / stats.norm(stats._long_dwell_clicks, False), 1.0 * session_stats.long_dwell_clicks / stats.norm(stats._long_dwell_clicks, True)]
        featurenames += [prefix + "longdwellclicks/ave_longdwellclicks_in_nonswitch_sessions", prefix + "longdwellclicks/ave_longdwellclicks_in_switch_sessions"]                
        features += [1.0 * session_stats.time_between_clicks / stats.norm(stats._time_between_clicks, False), 1.0 * session_stats.time_between_clicks / stats.norm(stats._time_between_clicks, True)]
        featurenames += [prefix + "time_between_clicks/ave_timebetweenclicks_in_nonswitch_sessions", prefix + "time_between_clicks/ave_timebetweenclicks_in_switch_sessions"]                        
        features += [1.0 * session_stats.is_last_click / stats.norm(stats._is_last_click, False), 1.0 * session_stats.is_last_click / stats.norm(stats._is_last_click, True)]
        featurenames += [prefix + "islastclick/ave_islastclick_in_nonswitch_sessions", prefix + "islastclick/ave_islastclick_in_switch_sessions"]                                
        features += [1.0 * session_stats.is_last_query / stats.norm(stats._is_last_query, False), 1.0 * session_stats.is_last_query / stats.norm(stats._is_last_query, True)]
        featurenames += [prefix + "islastquery/ave_islastquery_in_nonswitch_sessions", prefix + "islastquery/ave_islastquery_in_switch_sessions"]                                        
        return features

    def _get_features_callback(self, session):
        label = -1 if session["switchtype"] == "N" else 1        
        features = []
        featurenames = []
        stats = SessionStats(session)
        features += [1 if session["day"] % 7 == i else 0 for i in xrange(7)]
        featurenames += ["dayofweek = 0", "dayofweek = 1", "dayofweek = 2", "dayofweek = 3", "dayofweek = 4", "dayofweek = 5", "dayofweek = 6", ]
        features += [stats.queries_count]
        featurenames += ["queries_count",]
        features += [stats.clicks_count]
        featurenames += ["clicks_count",]
        features += [stats.actions_count]
        featurenames += ["actions_count",]
        features += [stats.time_1click]
        featurenames += ["time_1click",]
        features += [stats.abandoned]
        featurenames += ["abandoned",]
        features += [stats.ave_dwell]
        features += [stats.max_dwell]
        features += [stats.min_dwell]
        featurenames += ["ave_dwell", "max_dwell", "min_dwell"]
        features += [stats.clicks_per_query]
        featurenames += ["clicks_per_query",]
        features += [stats.duration]
        featurenames += ["duration",]
        features += [stats.unique_queries]
        featurenames += ["unique_queries",]
        features += [stats.duration_per_query]
        featurenames += ["_duration_per_query",]
        features += [stats.duration_per_action]
        featurenames += ["duration_per_action",]
        features += [stats.min_pause]
        features += [stats.ave_pause]
        features += [stats.max_pause]
        featurenames += ["min_pause", "ave_pause", "max_pause"]
        features += [stats.ave_click_pos]
        featurenames += ["ave_click_pos",]
        features += [stats.max_click_per_query]
        featurenames += ["max_click_per_query",]
        features += [stats.short_dwell_clicks]
        featurenames += ["short_dwell_clicks",]
        features += [stats.long_dwell_clicks]
        featurenames += ["long_dwell_clicks",]
        features += [stats.time_between_clicks]
        featurenames += ["time_between_clicks",]
        features += [stats.is_last_click]
        features += [stats.is_last_query]
        featurenames += ["is_last_click", "is_last_query"]
        features += self.norm_feats(stats, self._overal_stats, False, "total_", featurenames)
        features += self._overal_stats.get_query_features(stats, "total_", featurenames)
        features += self._overal_stats.get_url_features(stats, "total_", featurenames)

        featurenames1 = []
        featurenames2 = []
        prob1 = self._overal_stats.get_seq_prob(stats.action_seq, stats.extended_seq, stats.extended_seq2, False, "total_nonswitch_", featurenames1)
        prob2 = self._overal_stats.get_seq_prob(stats.action_seq, stats.extended_seq, stats.extended_seq2, True, "total_switch_", featurenames2)
        features += prob1
        features += prob2
        featurenames += featurenames1
        featurenames += featurenames2
        features += [ 1.0 * (prob1[i] + 1) / (prob2[i] + 1) for i in xrange(len(prob1))]
        featurenames += [ x + "_nonswitch_to_switch" for x in featurenames1]
        features += [ self._user_stats[session["user"]]._count[0] + self._user_stats[session["user"]]._count[1], 1.0 * (self._user_stats[session["user"]]._count[1] + 1.0) / (self._user_stats[session["user"]]._count[0] + self._user_stats[session["user"]]._count[1] + 10) ]
        featurenames += ["usersessions_count", "user_switchprob_smooth10"]
        features += self.norm_feats(stats, self._user_stats[session["user"]], True, "user_", featurenames)
        features += self._user_stats[session["user"]].get_query_features(stats, "user_", featurenames)
        features += self._user_stats[session["user"]].get_url_features(stats, "user_", featurenames)
        featurenames1 = []
        featurenames2 = []        
        prob1 = self._user_stats[session["user"]].get_seq_prob(stats.action_seq, stats.extended_seq, stats.extended_seq2, False, "user_nonswitch_", featurenames1)
        prob2 = self._user_stats[session["user"]].get_seq_prob(stats.action_seq, stats.extended_seq, stats.extended_seq2, True, "user_switch_", featurenames2)
        features += prob1
        features += prob2
        featurenames += featurenames1
        featurenames += featurenames2        
        features += [ 1.0 * (prob1[i] + 1) / (prob2[i] + 1) for i in xrange(len(prob1))]
        featurenames += [ x + "_nonswitch_to_switch" for x in featurenames1]

        # template = r"""<attribute name="%s" sourcecol="%d" valuetype="integer" blocktype="single_value" />"""
        # index = 1
        # print r"""<attributeset default_source="data_feats_8_comb_bal_small.txt">"""
        # for featname in featurenames:
        #     print template % (featname, index)
        #     index += 1
        # print r"""</attributeset>"""


        print >> self._out, str(label) + " " + " ".join([str(i + 1) + ":" + str(features[i]) for i in xrange(len(features))])

    def get_features(self, inputstream, outstream):
        self._out = outstream
        self.processSessions(inputstream, True, self._get_features_callback)

def readTraining(train_stats_file, train_file, train_feats_file):
    features_calc = FeatureCalculator()
    features_calc.build_filters(open(train_file, "r"))
    features_calc.collect_stats(open(train_stats_file, "r"))
    features_calc.get_features(open(train_file, "r"), open(train_feats_file, "w"))

def main(train_stats_file, train_file, train_feats_file):
    readTraining(train_stats_file, train_file, train_feats_file)

if __name__ == "__main__":
    main(argv[1], argv[2], argv[3])
