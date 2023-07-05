from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import os
import traceback
from utilities.helper import LLMHelper
from msal_streamlit_authentication import msal_authentication
import requests
import logging
logger = logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)

# Set favicon and page title
st.set_page_config(
    page_title="Search",
    page_icon="assets/logo.png",
    layout="wide"
)
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


list_access = ['arrajan@microsoft.com', 'cvermander@microsoft.com', 'shrutiwasnik@microsoft.com', 'apremsekhar@microsoft.com', 'v-vakaranam@microsoft.com', 'hax@microsoft.com', 'jmunnangi@microsoft.com', 'psheoran@microsoft.com', 'subhajch@microsoft.com', 'reastwood@microsoft.com', 'v-gkolla@microsoft.com', 'v-kolaks@microsoft.com', 'kmagaria@microsoft.com', 'mirechen@microsoft.com', 'deepbaldha@microsoft.com', 'chrajvir@microsoft.com', 'v-vavilala@microsoft.com', 'v-cbhat@microsoft.com', 'Wu.Linda@microsoft.com', 'yqu@microsoft.com', 'gaurav.kumar1@microsoft.com', 'manusre@microsoft.com', 'jeschwa@microsoft.com', 'chrichung@microsoft.com', 'antoniorod@microsoft.com', 'karthiks@microsoft.com', 'muhnassar@microsoft.com', 'jejosep@microsoft.com', 'Venkatesh.Boddu@microsoft.com', 'vsuryadevara@microsoft.com', 'rsharmab@microsoft.com', 'kritihedau@microsoft.com', 'bhanusingh@microsoft.com', 'brpotter@microsoft.com', 'v-csaibharat@microsoft.com', 'Gabrielle.Skladman@microsoft.com', 'hbindra@microsoft.com', 'v-vanapallis@microsoft.com', 'Yaoxian.Qu@microsoft.com', 'juhi.srivastava@microsoft.com', 'sshanbhogue@microsoft.com', 'kimallam@microsoft.com', 'akapula@microsoft.com', 'Michael.Rechenberg@microsoft.com', 'Chintan.Rajvir@microsoft.com', 'Jenna.Schwartz@microsoft.com', 'stankogutalj@microsoft.com', 'Karthikeyan.gopalan@microsoft.com', 'sachopr@microsoft.com', 'nicul@microsoft.com', 'addwived@microsoft.com', 'Jeffy.Joseph@microsoft.com', 'yurirubio@microsoft.com', 'ivanv@microsoft.com', 'Chan.Saeteurn@microsoft.com', 'gaskladm@microsoft.com', 'ksunkara@microsoft.com', 'snataraj@microsoft.com', 'vepaduch@microsoft.com', 'gbachani@microsoft.com', 'veboddu@microsoft.com', 'jsrivastava@microsoft.com', 'Kevin.Magarian@microsoft.com', 'mjohnst@microsoft.com', 'Aditya.Dwivedi@microsoft.com', 'prdesai@microsoft.com', 'v-ckishor@microsoft.com', 'dkolipaka@microsoft.com', 'jmathewjohn@microsoft.com', 'lindwu@microsoft.com', 'priyanshulnu@microsoft.com', 'vinerawa@microsoft.com', 'gaurakumar@microsoft.com', 'hpatidar@microsoft.com', 'Sana.Chopra@microsoft.com', 'rosode@microsoft.com', 'v-girs@microsoft.com', 't-divyapatel@microsoft.com', 'momorac@microsoft.com', 'arven@microsoft.com', 'Brandon.Potter@microsoft.com', 'v-sumannem@microsoft.com', 'csaeteur@microsoft.com', 'Pramit.Desai@microsoft.com', 'kravi@microsoft.com', 'ankursingla@microsoft.com', 'jian.sun@microsoft.com', 'Arvind.Venkataraman@microsoft.com', 'jiasu@microsoft.com','t-keertip@microsoft.com']

# MSAL Authentication
login_token = msal_authentication(
    auth={
        "clientId": "25af81bc-a78b-4fbb-b75f-ef52eed4f651",
        "authority": "https://login.microsoftonline.com/72f988bf-86f1-41af-91ab-2d7cd011db47",
        "redirectUri": "http://localhost:8501/",
        "postLogoutRedirectUri": "http://localhost:8501/"
        # "redirectUri": "https://sustainability-site.azurewebsites.net/",
        # "postLogoutRedirectUri":"https://sustainability-site.azurewebsites.net/"
    },
    cache={
        "cacheLocation": "sessionStorage",
        "storeAuthStateInCookie": True
    },
    login_request={
        "scopes": ["25af81bc-a78b-4fbb-b75f-ef52eed4f651/.default"]
    },
    login_button_text="Login",
    logout_button_text="Logout",
    key=1
)


if login_token is not None:  # Only execute the app if the user is authenticated
    member_of_sust = False
    
    if login_token['account']['username'] in list_access:
        member_of_sust = True

    
    if member_of_sust:
        with st.sidebar:
            st.session_state['custom_temperature'] = st.slider("Temprature", min_value=0.0, max_value=1.0, value=float(os.getenv("OPENAI_TEMPERATURE", 0.3)), step=0.1)
            st.header("About this")
            st.write("This is powered by the OpenAI's GPT-3.5 Turbo and is capable of answering your questions related to Microsoft Cloud for Sustainability.")
            # st.write(f"Hello, {login_token['account']['name']}")  # Display the authenticated user's name

        try:
            default_prompt = "" 
            default_question = "" 
            default_answer = ""
            search_index = "auto"

            if 'question' not in st.session_state:
                st.session_state['question'] = default_question
            if 'response' not in st.session_state:
                st.session_state['response'] = default_answer
            if 'context' not in st.session_state:
                st.session_state['context'] = ""
            if 'custom_prompt' not in st.session_state:
                st.session_state['custom_prompt'] = ""
            if 'custom_temperature' not in st.session_state:
                st.session_state['custom_temperature'] = float(os.getenv("OPENAI_TEMPERATURE", 0.3))
            if 'search_option' not in st.session_state:
                st.session_state['search_option'] = "auto"

            llm_helper = LLMHelper(custom_prompt=st.session_state.custom_prompt, temperature=st.session_state.custom_temperature)

            # Create a layout with three columns
            col1, col2, col3 = st.columns([1, 4, 1])

            with col1:
                search_index = st.selectbox("Index", [ "ado", "smes",  "sharepoint"])
            with col2:
                question = st.text_input("Query", default_question)
            with col3:
                st.write("")
                st.write("")
                search_button = st.button('Search')

            if (search_button or question != st.session_state['question']) and question != "":
                st.session_state['question'] = question
                st.session_state['question'], st.session_state['response'], st.session_state['context'], sources = llm_helper.get_semantic_answer_lang_chain_exp(question , search_index, [])
                st.markdown("###### Answer:") 
                st.markdown(st.session_state['response'])
                if search_index != "smes":
                    st.markdown("###### Sources:")
                    for src in sources:
                        URL = src['URL']; filenm = src['filename']
                        st.markdown(f'[{filenm}]({URL})')
                with st.expander("Question and Answer Context"):
                    st.markdown(st.session_state['context'].replace('$', '\$'))
                    

        except Exception:
            st.error(traceback.format_exc())

    else:
        st.error("You must be a member of the Microsoft Cloud for Sustainability team to use this application. Please contact the team to request access.")
else:  # If the user is not authenticated, display a message
    st.error("You must be logged in to use this application. Please use the login button above.")
