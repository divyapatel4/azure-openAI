import streamlit as st
from utilities.helper import LLMHelper
from msal_streamlit_authentication import msal_authentication

# Set favicon and page title
st.set_page_config(
    page_title="Chat",
    page_icon="assets/logo.png",
    layout="centered"
)

# Hide the Streamlit footer and hamburger menu
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
        # "redirectUri": "http://localhost:8501/",
        # "postLogoutRedirectUri": "http://localhost:8501/"
        "redirectUri": "https://sustainability-site.azurewebsites.net/",
        "postLogoutRedirectUri":"https://sustainability-site.azurewebsites.net/"
    },
    cache={
        "cacheLocation": "sessionStorage",
        "storeAuthStateInCookie": False
    },
    login_request={
        "scopes": ["25af81bc-a78b-4fbb-b75f-ef52eed4f651/.default"]
    },
    login_button_text="Login",
    logout_button_text="Logout",
    key=1
)
print(login_token)

if login_token is not None:
    member_of_sust = False
    if login_token['account']['username'] in list_access:
        member_of_sust = True
        print(login_token)
        
    if member_of_sust:
        # Set initial state
        if 'temperature' not in st.session_state:
            st.session_state['temperature'] = 0.3
        if 'question' not in st.session_state:
            st.session_state['question'] = None
        if 'chat_history' not in st.session_state:
            st.session_state['chat_history'] = []
        if 'source_documents' not in st.session_state:
            st.session_state['source_documents'] = []
        if 'Dropdown' not in st.session_state:
            st.session_state['Dropdown'] = "ado"

        # Helper functions to clear session state
        def clear_chat_data():
            st.session_state['question'] = ""
            st.session_state['chat_history'] = []
            st.session_state['source_documents'] = []

        def clear_text_input():
            st.session_state['question'] = st.session_state['input']
            st.session_state['input'] = ""

        # Initialize LLMHelper
        llm_helper = LLMHelper(temperature=st.session_state['temperature'])

        # Search bar, dropdown, and buttons on the top of the screen
        col1, col2, col3, col4 = st.columns([2,2.5,8,2])

        with col1:
            col1.write("")
            col1.write("")
            clear_chat = st.button("Clear", key="clear_chat", on_click=clear_chat_data)

        with col2:
            st.session_state['Dropdown'] = st.selectbox('Index:', ['ado', 'smes', 'sharepoint'])

        with col3:
            st.text_input("Search:", placeholder="type your question", key="input", on_change=clear_text_input)

        with col4:
            col4.write("")
            col4.write("")
            search = st.button("search", key="search")

        # Sidebar
        with st.sidebar:    
            st.header("About this")
            st.session_state['temperature'] = st.slider("Temperature", min_value=0.0, max_value=1.0, value=st.session_state['temperature'], step=0.1)
            st.write("This page is still work in progress use this only if your answers depends on your previous questions otherwise prefer the search page.")
            st.write("This is powered by the OpenAI's DaVinci-003 and is capable of answering your questions related to Microsoft Cloud for Sustainability.")

        if st.session_state['question']:
            with st.spinner('Searching for answers...'):
                question, result, _, sources = llm_helper.get_semantic_answer_lang_chain(st.session_state['question'], str(st.session_state['Dropdown']).lower() , st.session_state['chat_history'])
                
            st.session_state['question'] = None
            st.session_state['chat_history'].append((question, result))
            st.session_state['source_documents'].append(sources)

        if st.session_state['chat_history']:
            for i in range(len(st.session_state['chat_history']) - 1, -1, -1):  # reverse the order
                with st.container():
                    st.markdown("<div style='background-color:lightgrey; padding:4px; border-radius:10px'>", unsafe_allow_html=True)
                    st.markdown(f"**Question:**")
                    st.markdown(st.session_state['chat_history'][i][0])
                    st.markdown(f"**Results:**")
                    st.markdown(st.session_state['chat_history'][i][1])
                    st.markdown("</div>", unsafe_allow_html=True)
                    current_sources = st.session_state['source_documents'][i]

                    # Give sources if current index is not smes and length of current sources is not 0
                    if st.session_state['Dropdown'] != 'smes' and len(current_sources) != 0:
                        st.markdown("###### Sources:")
                        source_links = []
                        for src in current_sources:
                            URL = src['URL']
                            filename = src['filename']
                            source_links.append(f'[{filename}]({URL})')
                        st.markdown("  ,   ".join(source_links))

        st.write("\n"*50)  # spacer
    else:
        st.error("You must be a member of the Microsoft Cloud for Sustainability team to use this application. Please contact the team to request access.")
else:  # If the user is not authenticated, display a message
    st.error("You must be logged in to use this application. Please use the login button above.")
