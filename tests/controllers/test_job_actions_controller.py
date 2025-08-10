"""
Unit tests for JobActionsController

Tests all methods of the JobActionsController including:
- like_job and unlike_job functionality
- save_job and unsave_job functionality  
- share_job functionality
- get_job_actions_state functionality
- Error handling and validation
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.controllers.jobs.actions import JobActionsController
from src.database.models import JobLike, JobShare, SavedJob, JobActionsState, ShareMethodEnum
from src.database import JobLikeORM, JobShareORM, SavedJobORM, JobsORM, JobSeekerProfileORM


class TestJobActionsController:
    """Test cases for JobActionsController"""

    @pytest.fixture
    def mock_factory(self):
        """Create mock factory for controller initialization"""
        factory = Mock()
        return factory

    @pytest.fixture
    def controller(self, mock_factory):
        """Create JobActionsController instance for testing"""
        controller = JobActionsController(mock_factory)
        controller.logger = Mock()
        controller.analytics_service = Mock()
        return controller

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        return session


class TestLikeJobFunctionality:
    """Test like_job and unlike_job methods"""

    @pytest.fixture
    def controller(self):
        factory = Mock()
        controller = JobActionsController(factory)
        controller.logger = Mock()
        controller.analytics_service = Mock()
        return controller

    @pytest.mark.asyncio
    async def test_like_job_success(self, controller):
        """Test successful job like"""
        # Mock session and database queries
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock user and job existence
        mock_user = Mock()
        mock_job = Mock()
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_user,  # User exists
            mock_job,  # Job exists
            None  # No existing like
        ]

        # Mock like count query
        mock_session.query.return_value.filter_by.return_value.scalar.return_value = 5

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.like_job("user123", "job456")

        assert result["success"] is True
        assert result["message"] == "Job liked successfully"
        assert "like_id" in result["data"]
        assert result["data"]["like_count"] == 5

        # Verify analytics tracking was called
        controller.analytics_service.track_job_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_like_job_invalid_ids(self, controller):
        """Test like_job with invalid user or job IDs"""
        result = await controller.like_job("", "job456")
        assert result["success"] is False
        assert result["code"] == 400

        result = await controller.like_job("user123", "")
        assert result["success"] is False
        assert result["code"] == 400

    @pytest.mark.asyncio
    async def test_like_job_user_not_found(self, controller):
        """Test like_job when user doesn't exist"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock user not found, job exists
        mock_job = Mock()
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # User not found
            mock_job  # Job exists
        ]

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.like_job("user123", "job456")

        assert result["success"] is False
        assert result["code"] == 404
        assert result["message"] == "User not found"

    @pytest.mark.asyncio
    async def test_like_job_already_liked(self, controller):
        """Test like_job when job is already liked"""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock user and job exist, existing like found
        mock_user = Mock()
        mock_job = Mock()
        mock_existing_like = Mock()
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_user,  # User exists
            mock_job,  # Job exists
            mock_existing_like  # Existing like found
        ]

        controller.get_session = Mock(return_value=mock_session)

        result = await controller.like_job("user123", "job456")

        assert result["success"] is False
        assert result["code"] == 409
        assert result["message"] == "Job already liked"


@pytest.mark.asyncio


async def test_unlike_job_success(self, controller):
    """Test successful job unlike"""
    mock_sessione__])ain([__filpytest.m  ':


____mainame__ == '_n

if _ 0
"] ==ike_countdata"]["le_result[" unlik
assert ue
Trcess
"] is "
sucike_result[t
unl
asser
"job456")", 3b("
user12r.unlike_jo
controllet = await_resul
unlikeike
nl
Test
u
# = 0
n_value
scalar.retur_value.r_by.
return.filteturn_valuequery.ression.mock_seike
isting_l = mock_exreturn_valuee.first.return_valufilter_by.n_value.query.retur_session.mockk()
g_like = Mocmock_existin
ock()
.reset_mmock_session
like
ks
for unset mocRe  #
is True
ss
"]cce"
suke_result[
assert li
b456
")
, "jor123""usejob(.like_t controllerult = awaike_res li  ike
# Test l

on)k_sessiue = mock(return_val=Mocsion
ller.get_ses
contro
ue = 1
allar.return_vlue.scareturn_vae.filter_by.turn_valury.resion.queck_ses
mo]
e
iksting
l
exi  # No   None
existsob,  # Job   mock_j     exists
User
ck_user,  # mot = [
side_effecalue.first.by.return_vlue.filter_.return_vassion.query
mock_se = Mock()
_job
mock
ock()
ser = M_u
mock
g
like)
o
existinike_job(nll: lt
caFirs  #
None)
n_value = ck(returt__=Moxision.__e
mock_ses
ession)lue = mock_sturn_va(re
Mock_ = r_ssion.__entemock_se()
ockion = Mss_seock
m
"""
 ike flowunlke -> complete li""Test  "):
       trollerconow(self, nlike_fl_ulete_like_comp def testo
    async.asyncitest.mark @py
   r
    ontrolle return c     
  Mock()vice = ytics_seroller.analcontr      ck()
  .logger = Mollercontro      tory)
  roller(facnsContbActio = Jooller     contr Mock()
    =     factory
   lf):seontroller(f c  defixture
      @pytest.""
    
roller"ctionsContbA for Jotsn testioegra""Int"ion:
    gratnsIntestJobActio

class Ter error"
ternal serve"Inage"] == ["mess result   assert500
     ode"] == "cresult[  assert e
      "] is Falsst["succes resul     assert    
   ")
    456", "job"user123r.like_job(olletrit con= awa    result    
         sion)
ck_sese=moreturn_valuion = Mock(er.get_sess   controll
             iled")
on faase connectition("Databfect = Excepy.side_efsession.quer     mock_
   se errorataback d    # Mo
       )
     n_value=Noneetur(rockxit__ = Mn.__esessio   mock_
     on)essi=mock_sreturn_valuek( Moc.__enter__ =k_session      moc  Mock()
ssion = ck_se mo       "
rrors""abase eatdling of dan""Test h
        "ntroller):ing(self, coandl_error_hseataba def test_d  asyncsyncio
  ark.aest.m    @pytalse
    
, None) is Fr123""use_job_ids(te_user_and_validaler.t control   asser      False
ob456") ise, "jds(Nonnd_job_idate_user_a._valicontrollerssert   a   se
   Fal "") is 123",b_ids("userjond__user_a_validate controller.sert as       ) is False
""job456("", job_ids_user_and_teller._valida contro assert     
  """
lid
IDsvan
with inst validatioTe""":
        oller)ontr calid(self,job_ids_invte_user_and_idat_valdef tes
    
     is True resultert   ass)
     "job456"", 23ds("user1and_job_ilidate_user_troller._vaonesult = c"
        rid IDs"" valwithion lidatva"""Test:
    controller)lf, ds_valid(seob_iand_jte_user_t_valida


def tes  ntroller


co
return k()
Moc = er.logger
controlltory)
(faclertionsControler = JobActroll       con()
tory = Mock
fac):lfroller(se


def cont.


    fixture
test


@py


g
"""
  lin handd errorethods ann malidatio"Test v ""  :
 nsValidationctiotJobA
class Tes] == 0

_count""]["shareaesult["dat   assert r    t"] == 0
 ike_coundata"]["lesult["ert r       ass
 lsed"] is Fahas_saveuser_]["t["data"sert resul
        asis Falseed"] user_has_lik"data"]["[resultrt  asse    ue
   "] is Tresscclt["susu  assert re  
           6")
 "job4523", user1ons_state("b_actiler.get_joait controlesult = aw  r 
      on)
       k_sessiue=mocturn_val(re= Mockession ler.get_scontrol
                 ]
    e count
    Shar #         0  t
   e coun # Lik     0, 
        [de_effect =.sialue.scalarby.return_vue.filter_.return_valn.querymock_sessio       queries
 ock count  M    #     
         ]
   saved
   ser hasn't None   # U     ked
       asn't lir hUse   None,  #      
    = [side_effect t..firseturn_valueer_by.rlue.filtry.return_vaion.que  mock_sess    ns found
  tiouser acno Mock    #             
one)
 =Nreturn_valueock(__ = M__exitsession.    mock_sion)
    ck_sesurn_value=mo(retter__ = Mocksession.__enk_    moc()
    ock Mession =ock_s      m
  ons"""
o
actiser
has
nstate
when
us
job
actiont
"""Tes
 :ler) controlf,seltions(state_no_acactions_b_est_get_joc def t  asyncio
rk.asynpytest.ma @
] == 5
_count""]["shareatalt["d assert resu     = 10
count"] ="like_]["sult["data re  assert      is True
] ved"as_sa"]["user_hult["dataesassert r        rue
"] is Tas_likedser_hdata"]["uesult["t rasser    t
 in resulrt "data"asse   e
 "] is Trusuccessesult["ssert r   a    
   ")
456"jober123", s_state("usjob_actionget_oller.ait contr = aw     result   
ion)
 ck_sessrn_value=moMock(retusession = get_ler.   control    
          ]
re count
# Sha   5      t
 e coun  10,  # Lik         t = [
.side_effecvalue.scalarr_by.return_value.filtereturn_y.ion.quer mock_sesss
   count querie  # Mock    
     ]
 
 )Nonesaved (not User has Mock()   #            ot None)
ed (nlikr has ),  # Use     Mock(    
effect = [rst.side_.fialueeturn_v.rue.filter_byn_valery.returon.qu  mock_sessi  ts
d counan actions  userqueries for     # Mock 

    ue=None)k(return_valexit__ = Mocession.__k_s        mocsion)
mock_seseturn_value== Mock(r__ ersion.__entock_ses    mock()
sion = M_ses mock"
   e""s statf job action oul retrievalssfccet su""Tes    "    ller):
controlf, ccess(seons_state_sucti_job_ast_getync def teio
ast.mark.async    @pytesller

eturn contro       r = Mock()
r.loggercontrolley)
    oller(factoronsControbActi Jroller =     cont
= Mock()     factory
f):troller(selcon
def rextuytest.fi@p    "

"hod"ete mtions_statb_acest get_jo""T "
sState:JobActionsts Te

clasund"
ob not fo] == "J"["messageultrt ressse        a404
code"] == lt["rt resu      asse  lse
ss"] is Fa"succesult[sert re
    as  n")
  linkedijob456", "23", "r1re_job("usetroller.shait con = awa   result  
 
  ssion)ue=mock_sern_valetu Mock(rt_session =ontroller.ge       c      
ue = None
t.return_val.firsurn_valuer_by.retue.filtern_valtuy.reuern.qioess  mock_sd
  not foun # Mock job 
        
lue=None)k(return_va_ = Mocexit__session.__     mocksion)
sesock_value=m(return_ter__ = Mockion.__enk_sess   moc   ck()
session = Mo mock_     
exist"""
n
't doeshen job job west share_   """Tler):
ontrollf, cund(set_fob_job_nojo
test_share_def    async ncio
mark.asytest. @ py

re
method
"Invalid sha== "] ssage
"esult["
meert
r
ass = 400
"code"] =t[esulrt
r
asse
s
False
iuccess
"]["
sultsert
res as

d_method
")li6", "inva "
job45er123
","
usjob(.share_controllerait
result = aw
"
e
method
""
id
sharith
inval_job
w
share
"Test""        oller):
lf, contrd_method(seob_invalihare_jt_sc


def tes
    asyncioark.asyn @ pytest.m


us
for anonymol code erra No refs None  # ide"]"referral_co"data"][t result[  assery"
lled
successfu = "Job sharge"] =["messassert result
arue] is Tccess
"["
sultesut
rasser

"email")56
",ne, "
job4ob(Nor.share_jt
controlleesult = awai
r
)
ionsess = mock_valueck(return_Mon=ioget_sessontroller.c
ue = 1
alturn_ve.scalar.return_valulter_by.rern_value.fin.query.retuessio
mock_s
count
hare
Mock
s
#
mock_joblue = n_vairst.returue.fvalreturn_ilter_by.urn_value.fery.retk_session.qu
mocock()
ob = Mock_j
m
job
exists
# Mock
)
n_value = Noneck(returexit__=Mo_session.__ckmo
ock_session)ue = murn_valMock(retenter__=sion.__
mock_ses)
ion = Mock(mock_sess
""
cation
"hentiutthout ahare wi sful jobest success""T   "
ler):
f, control_success(selusb_anonymoe_jo_sharnc


def test


    asymark.asyncio @ pytest.

3
count
"] ==e_"
shardata
"][esult["
assert r
"data"] result[code
" ineferral_  assert "
r]
t["data"" in resulshare_idert "
ass
fully
"essccb shared su] == "
Jo["message"
ltrt
resu
asse
e
Truss
"] is ucceesult["
srt
r
asse

edin
")ink"
l456
",  "
jobr123
",b("
useer.share_jooll
await contr
result =
ssion)
ock_seturn_value = mre
Mock(et_session=ntroller.g
co
3
= valuen_calar.returrn_value.ster_by.retufilurn_value.uery.retion.q
mock_sess
nt
k
share
couMoc
#  ]
xists
User
eer  # ck_us  mo     sts
Job
exik_job,  # moc    [
effect = first.side_urn_value.ilter_by.ret_value.frnry.retun.queio
mock_sess)
r = Mock(mock_use
         =Mock()
ob
mock_j
str
exijob and use
Mock  #

alue = None)(return_vock = M_exit__session._    mock_    n)
sessiock_e = moreturn_valuer__ = Mock(on.__entck_sessi
mo
Mock()
ck_session =
mo
""
ser
"icated uth authentwi job share  successful"
Test
""
oller):ontrcess(self, ccated_sucthentiaure_job_f
test_shade
async iork.async

@pytest.ma


ntrollerrn
cotu
re)vice = Mock(er_sr.analyticscontrolle)
ger = Mock(r.log
controlle
(factory)
erontrollJobActionsCler = ntrolco
ck()
ory = Mo
fact):
ler(selfcontrol


def
    xture @ pytest.fi


""
hod
" metobe_j""Test shar "
nality:
FunctioTestShareJob


class e()ed_oncsert_callon.commit.asssi  mock_se   )
isting_saveexock_with(med_once_ert_callete.assdelsession.k_       mocas called


delete
wfy  # Veri

ully
"ssfsuccesaved  "
Job
un
"] ==agess result["
me
assert
is Truesuccess
"] result["
assert
)
b456
"joer123", "ob("
ussave_jontroller.unait
caw
result =
ion)
ss = mock_sevalueck(return_ssion=Mo_segetoller.contr
ting_save
exise = mock_eturn_valut.rirsrn_value.flter_by.retue.fialu_vrnry.retun.queessiock_s
mo       )
save = Mock(xisting_
mock_eound
fg
saveistin  # Mock ex

ue = None)return_val = Mock(n.__exit__
ssio
mock_seion)
ue = mock_sessturn_val(reter__=Mock_enion._ck_sess
mo
Mock()
on = k_sessi
mocave
"""ul job unsccessf""Test su        "ntroller):
(self, coesscce_job_susavst_unnc def teio
    asyark.asyncst.mpyte   @    
 "
aved already s= "Job] =ssage"esult["me   assert r    
 409"] == "codeult[sert res
        as] is Falsecess""suc result[rt asse          
   
  456")", "job3"user12er.save_job(rollcont await lt =     resu
       on)
    essik_s_value=mocrn Mock(retussion =get_seoller.ntr  co   
              ]
found
     ing save  Existve  #isting_sa  mock_ex       ts
   ob exis J     #      mock_job,      s
      er exist# Us    r,      se    mock_u [
        ect =effst.side_alue.fir_v.returnbyr_teue.fileturn_valy.rquersession.       mock_
 ck()ve = Moexisting_sa    mock_Mock()
    ck_job =     mo
    ock()= Mer    mock_us
     e foundting sav exisjob exist,r and ck use # Mo       
        ne)
rn_value=No(retut__ = Mockexi__n._sessio        mockession)
value=mock_srn_ock(retu_enter__ = Mck_session._    mo
    = Mock()ssion ck_se    mo  ""
  ady saved"b is alrejob when jot save_  """
Tes      ):
, controllerd(selflready_saveob_a_save_j


def testo
    asyncciasynt.mark.pytes @ e()


called_oncsert_b_action.ask_joervice.tracalytics_sroller.an
cont
d
as callecking
wtray
analytics  # Verif

a
"]"
dat in result[ved_job_id
"ert "
sa
ass
ully
"
successfob
savedge
"] == "
Jlt["messassert resu
a is True
"success"][ltssert resu
           a      456")
                     "job23", ("user1ob.save_jontrollerwait cesult = a   r
                               )
           ck_sessione = mon_valu
Mock(retur=ionssoller.get_se
contr
]
save
isting
exNo  # ne    No        sts
ob
exi  # Job,      mock_j      exists
,  # User  mock_user
ect = [t.side_effrse.fiurn_valu_by.ret.filteraluey.return_vssion.querock_se
       mck()_job = Mo
mock
= Mock()
mock_user
ve
g
sainistst, no
exnd
job
exiser
a  # Mock u
None)
value = ock(return___=Msion.__exit
mock_ses       )
_session = mockaluereturn_vck(enter__=Mossion.__
mock_sek()
Mocck_session =
mo
"""eav job st successful """
Tes
ller):
self, controcess(ve_job_suct_saesf
tasync
de
asyncio
test.mark.
@ py
controllerurn
ret = Mock()
cs_service.analytiontroller
c
Mock()
r.logger = controlle
ry)
ller(factoctionsController=JobAro
contMock()
tory = facself):
oller(f
contrure
deixtst.fpyte @
ods
"""
ave_job methnsve_job and u"Test sa:
    ""alityeJobFunctiontSavlass Tes
cd"

 founotike n"Le"] == essagult["mrt res  asse4
      40ode"] == "c[esult  assert r
      False is "success"]t result[ser   as       
     b456")
  "jo23",user1"nlike_job(.uler control = awaitlt   resu  
        sion)
   =mock_sesaluern_v = Mock(retuessiont_sler.gentrol    co   
    e
     = Nonurn_value first.retue.eturn_valy.rer_b.filtturn_valuery.re.quemock_session
        ke foundting li no exisckMo       # 
        
 e)_value=Nonturnk(re Moc.__exit__ =k_session  moc
      sion)ock_sesalue=meturn_v_ = Mock(r_enter__session._mock        k()
ocion = Mck_sess
        mo"""'t existlike doesnn he_job w"Test unlike   ""     ):
ntrollerund(self, co_not_fo_unlike_jobc


def test asyn.asyncio


est.mark @ pyt

()
ed_once_callssertommit.asion.c
mock_ses_like)
xistingth(mock_eed_once_wiert_call.asssion.delete
mock_sesed
was
callelete
y
d  # Verif
== 4
nt
"]e_couikdata"]["l["ultert resss     a
lly
"ed successfu unlik == "
Jobsage
"]"
mesesult[
assert r
rue
cess
"] is Tuc result["
s
assert
job456
")
"23", ob("user1ler.unlike_jt controlawai result =   
n)
_sessiockmon_value = urk(retession=Mocroller.get_s
cont
= 4
eturn_value
scalar.re.return_valuer_by._value.filtturnry.re_session.queck
motion
ter
delet
afounck
like
c  # Mo

ng_likeexistiue = mock_alt.return_ve.firsreturn_valur_by.lue.filtery.return_vaon.quesessi
mock_()
= Mocklike
ck_existing_
mod
ounlike
fisting
ock
ex  # M
lue = None)
rn_va = Mock(retut__.__exiock_session
m
ession)mock_sn_value = tur = Mock(re_enter__
sion._
mock_ses)
Mock( =
