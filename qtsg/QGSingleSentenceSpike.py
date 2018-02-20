"""
Investigation how to get sync grammar to relate sentences to highlights
"""


from config import Config
from parse import POSTagger, PhraseDependencyTree
from nlputils import NltkUtils
from features import ExtractFeatures
from utils import ListFiles
from tasks import CNNAssessmentFiles, BBCCaptionFilelist, DUC04Filelist
from summarize import WriteHighlights
from features.FeatureList import *
from nlputils import TfIdf
from nlputils.TfIdf import CorpusFreqDist
import nltk.probability
import cPickle as pickle
import sys, os, codecs


# all the core functions of QG
from SyncTreeGrammar import *

PRINT_DEBUG = False
PRINT_INFO = False

# Various sentences and highlights from the corpus
#canada.mad.cow
eg_ca_t1="There was no risk to public health because no part of the animal entered the human food systems , government inspectors said ."
eg_ca_t2="The Canadian Food Inspection Agency said Monday that the latest case of mad cow disease , also known as bovine spongiform encephalopathy , or BSE , does not suggest the problem is more widespread ."
eg_ca_t3="Luterbach said Canada has been assessed by the World Organization for Animal Health and given a controlled-risk status , indicating it has the proper checks and balances to control the disease ."
eg_ca_t4="Luterbach said more than 220,000 cattle in Canada have been tested for BSE since the country 's first case in 2003 ."
eg_ca_h1="Canadian agency : Latest case does n't suggest the problem is more widespread ."
eg_ca_h2="No part of animal entered human food systems , government inspectors say ."
eg_ca_h3="Official says Canada has proper checks and balances to control disease ."
eg_ca_h4="More than 220,000 cattle in Canada tested for disease since first case in 2003 ."

# church.conference
eg_ch_h1="Lambeth Conference , held every decade , brings together Anglican church leaders ."
eg_ch_h2="Some bishops have boycotted event over gay clergy and female bishops ."
eg_ch_h3="Conservative Anglican bishops decided last month to form their own movement ."
eg_ch_h4="Anglican Communion is 3rd biggest church in the world , has 80M members ."
eg_ch_t1="Controversy over gay clergy and female bishops is likely to dominate the Anglican church 's once-a-decade conference , which begins Wednesday ."
eg_ch_t2="The Lambeth Conference in Canterbury , southern England , brings together archbishops and bishops from the Anglican church around the world ."
eg_ch_t3="But many invited bishops are boycotting the event , angry that the church allowed the consecration of a gay bishop in the United States in 2003 ."
eg_ch_t4="Conservative Anglican bishops decided last month to form their own movement , The Fellowship of Confessing Anglicans , to counter what they see as the liberalization of the church ."
eg_ch_t5="The row has triggered speculation about a split in the Anglican Church , the third-largest church in the world after the Roman Catholic Church and the Orthodox Church ."

# england.cech.ap2008
eg_en_h1="Chelsea goalkeeper Petr Cech has signed a new five-year contract ."
eg_en_h2="The Czech Republic player joined from Rennes in 2004 ."
eg_en_h3="The 26-year-old has made 115 appearances for the London club ."
eg_en_t1="Chelsea goalkeeper Petr Cech has signed a new five-year contract to keep him at the club until 2013 ."
eg_en_t2="The 26-year-old Cech has made 115 appearances for Chelsea since joining from French club Rennes in 2004 ."

# iraq.diplomacy2008
eg_ir_h1="Iraqi PM al-Maliki due to meet German leaders , Italian leaders , pope next week ."
eg_ir_h2="Al-Maliki met a leading Lebanese lawmaker in Baghdad on Thursday ."
eg_ir_h3="Iraqi government is seeking closer diplomatic ties with rest of Arab world ."
eg_ir_t1="The government said on Thursday that Iraq 's prime minister , Nuri al-Maliki , is meeting next week with the leaders of Germany and Italy and with the pope ."
eg_ir_t2="The government also announced the meeting in Baghdad on Thursday between al-Maliki and Saad Hariri , a top Lebanese lawmaker ."
eg_ir_t3="Iraq has been urging other countries to establish ties with it and has urged the Arab world to name ambassadors and open their embassies in the country ."


# king.poll2009
eg_ki_h1="69 percent of blacks polled say Martin Luther King Jr 's vision realized ."
eg_ki_h2="Slim majority of whites say King 's vision not fulfilled ."
eg_ki_h3="King gave his `` I have a dream '' speech in 1963 ."
eg_ki_t1="The poll found 69 percent of blacks said King 's vision has been fulfilled in the more than 45 years since his 1963 ` I have a dream ' speech -- roughly double the 34 percent who agreed with that assessment in a similar poll taken last March ."
eg_ki_t2="` Whites do n't feel the same way -- a majority of them say that the country has not yet fulfilled King 's vision , ' CNN polling director Keating Holland said ."

# brazil.traffickers2009
eg_br_h1="Two schools , offices closed in three Rio de Janeiro neighborhoods during shootouts ."
eg_br_h2="At least 10 drug-trafficking suspects killed in confrontations with police , agency says ."
eg_br_h3="Woman also wounded , in critical condition ."
eg_br_h4="Rio has been plagued by violence ; many deaths reportedly from drug-trafficking fights ."
eg_br_t1="Police have killed at least 10 drug-trafficking suspects in all-day shootouts in Brazil that closed schools and government offices in three Rio de Janeiro neighborhoods , the official news agency said ."
eg_br_t2="A woman was wounded and in critical condition , the news agency said , citing the state 's health minister ."
eg_br_t3="Two schools were closed , and 6,600 students were sent home ."
eg_br_t4="Rio has been plagued by a wave of violence that led to protests in December by a group called Rio de Paz ."
eg_br_t5="Many of the deaths come from drug traffickers fighting for territory in Rio 's slums and poor neighborhoods , said the group 's president , Antonio Carlos Costa ."

# california.helicopter2009
eg_cal_h1="U.S. Border Patrol helicopter crashes near San Onofre Nuclear Generating Station ."
eg_cal_h2="Helicopter was headed to airport in San Diego ."
eg_cal_h3="Three people on helicopter were taken to hospital with non-life-threatening injuries ."
eg_cal_t1="A U.S. Border Patrol helicopter went down Thursday night near the San Onofre Nuclear Generating Station , the FAA said ."
eg_cal_t2="The helicopter was going from the airport in Long Beach , California , to the Brown Field airport in San Diego , said Vince Bond , the Border Patrol 's public information officer ."
eg_cal_t3="The three people were able to exit the helicopter on their own and were taken to a hospital with non-life-threatening injuries ."

# china.pirates2009
eg_cp_h1="NEW : French merchant ship and nine crew released at weekend , owners say ."
eg_cp_h2="15 vessels have requested protection from China 's fleet in the gulf ."
eg_cp_h3="It 's the first time Chinese naval vessels have left Chinese waters in centuries ."
eg_cp_h4="Pirates have hijacked nearly 40 vessels off the coast of Somalia ."
eg_cp_t1="Pirates have released a French merchant ship and its nine crew members seized off the Nigerian coast over the weekend , the ship 's owners said Wednesday ."
eg_cp_t2="Meanwhile , the Chinese convoy -- which left some two weeks ago on a mission to protect Chinese merchant ships from an increasing number of pirate attacks occurring in the gulf -- has received requests for help from at least 15 vessels , according to news reports ."
eg_cp_t3="It marks the first time Chinese naval vessels have left Chinese waters in centuries ."
eg_cp_t4="Figures from the International Maritime Bureau for the year-to-date show pirates have attacked almost 100 vessels and hijacked nearly 40 off the coast of Somalia ."

# facebook.democracy
eg_fa_t1="A week after a policy-change blunder sparked widespread protests , the Web 's most popular social-networking site announced a new approach Thursday to give users more control over future Facebook rules and practices ."
eg_fa_h1="New approach will give users more control over Facebook policies and practices ."

# holder.swearing
eg_ho_t1="By a 75-21 vote , the U.S. Senate on Monday confirmed President Obama 's nomination of Holder ."
eg_ho_t2="Holder , 58 , is a former federal prosecutor and served as deputy attorney general during the Clinton administration ."
eg_ho_h1="Senate confirmed his appointment Monday on 75-21 vote ."
eg_ho_h2="He is a former federal prosecutor , deputy attorney general ."

# colombia.cross
eg_col_t1="Colombian President Alvaro Uribe admitted Wednesday that the symbol of the neutral Red Cross organization was used in a hostage rescue mission that freed 15 people from leftist rebels two weeks ago ."
eg_col_h1="President Alvaro Uribe says the Red Cross symbol was used in hostage rescue ."


# todo: sort out parsing and caching
# dpParser = POSTagger.StanfordDependencyParser()
# pennParser = POSTagger.StanfordPennParser()
graphvizDir = Config.GRAPHVIZ_DIR
FORMAT="ps"
GRAPHVIZ_EXTRA = False
MIN_PHRASE_SIZE = 1



def investigate(doc):
    sl_ca = [ (eg_ca_t1, eg_ca_h2), 
              (eg_ca_t2, eg_ca_h1),
              (eg_ca_t3, eg_ca_h3), 
              (eg_ca_t4, eg_ca_h4) ]
    sl_ch = [ (eg_ch_t2, eg_ch_h1),
              (eg_ch_t3, eg_ch_h2),
              (eg_ch_t4, eg_ch_h3),
              (eg_ch_t5, eg_ch_h4), ]
    sl_en = [ (eg_en_t1, eg_en_h1),
              (eg_en_t2, eg_en_h2),
              (eg_en_t2, eg_en_h3) ]
    sl_ir = [ (eg_ir_t1, eg_ir_h1),
              (eg_ir_t2, eg_ir_h2),
              (eg_ir_t3, eg_ir_h3) ]
    sl_ki = [ (eg_ki_t1, eg_ki_h1),
              (eg_ki_t2, eg_ki_h2),
              (eg_ki_t1, eg_ki_h3) ]
    sl_br = [ (eg_br_t1, eg_br_h1),
              (eg_br_t1, eg_br_h2),
              (eg_br_t2, eg_br_h3),
              (eg_br_t4, eg_br_h4),
              (eg_br_t5, eg_br_h4) ]
    sl_cal= [ (eg_cal_t1, eg_cal_h1),
              (eg_cal_t2, eg_cal_h2),
              (eg_cal_t3, eg_cal_h3) ]
    sl_cp = [ (eg_cp_t1, eg_cp_h1),
              (eg_cp_t2, eg_cp_h2),
              (eg_cp_t3, eg_cp_h3),
              (eg_cp_t4, eg_cp_h4) ]
    sl_fa = [ (eg_fa_t1, eg_fa_h1) ]
    sl_ho = [ (eg_ho_t1, eg_ho_h1),
              (eg_ho_t2, eg_ho_h2) ]
    sl_col = [ (eg_col_t1, eg_col_h1) ]
    
    
    

    currentSentencePair = sl_cal[2]
    #createParserTreeDiagrams(sl_cal[2])
    fullResultsList = []
    
    count = 0
    
    # sets involving word modification
    #for currentSentencePair in sl_cal[1:2] + sl_col:
    
    # full set
    for currentSentencePair in sl_ca + sl_ch + sl_en + sl_ir + \
        sl_ki + sl_br + sl_cal + sl_cp + sl_fa + sl_ho + sl_col:

        tText1 = createTree(currentSentencePair[0],doc)
        tHighlight1 = createTree(currentSentencePair[1],doc)
        
        print
        print "Source text tree:"
        print tText1.pprint()
        print
        print "Target text tree:"
        print tHighlight1.pprint()
        
        results = syncGrammar( tText1, tHighlight1 )
        fullResultsList.extend(results)
        #printRulesAndExamples(results)
        
        
        # raise SystemExit
        count += 1
        # if count > 1: break
            
        
    print
    print "Sync grammar generation completed"
    printResultsListInfo( fullResultsList )
    
    print
    print "Full rule list"
    printRules( fullResultsList ) 



