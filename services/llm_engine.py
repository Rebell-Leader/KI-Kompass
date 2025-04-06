import os
from langchain_community.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain

# Get API key from environment variable
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Initialize embeddings
def get_embeddings():
    return OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Initialize language model
def get_llm():
    return ChatOpenAI(
        temperature=0.7,
        model_name="gpt-3.5-turbo",
        openai_api_key=OPENAI_API_KEY
    )

# Get knowledge base for relocation to Munich
def get_knowledge_base():
    """
    Creates or loads a Qdrant vector store for relocation knowledge.
    
    In a production environment, you would:
    1. Ingest documents about relocation to Munich
    2. Split them into chunks
    3. Create embeddings and store in Qdrant
    
    For this MVP, we're creating a simple in-memory store with a few key pieces of information.
    """
    embeddings = get_embeddings()
    
    # Define some key pieces of information about relocating to Munich
    texts = [
        # Anmeldung (Registration)
        "When you move to Munich, you must register your address at the local Bürgerbüro (citizen's office) within 14 days of arrival. This process is called 'Anmeldung'. You'll need your passport and a confirmation from your landlord (Wohnungsgeberbestätigung).",
        
        # Tax ID
        "After registering your address, you'll receive your tax identification number (Steuer-ID) by mail within 2-4 weeks. You'll need this for employment in Germany.",
        
        # Residence Permit
        "Non-EU citizens must apply for a residence permit at the Foreign Office (Ausländerbehörde) within 90 days of arrival or before their visa expires. Required documents typically include passport, biometric photos, proof of address, proof of health insurance, and proof of financial means.",
        
        # Health Insurance
        "Health insurance is mandatory in Germany. Public health insurance (gesetzliche Krankenversicherung) is provided by various companies like TK, AOK, or Barmer. If you're employed, your employer will register you and split the cost. Self-employed individuals can choose between public and private insurance.",
        
        # Bank Account
        "Opening a bank account (Girokonto) is essential for rent payments, receiving salary, and daily transactions. Popular options include Deutsche Bank, Commerzbank, and online banks like N26 or DKB. You'll need your passport and registration certificate (Anmeldebestätigung).",
        
        # Transportation
        "Munich has an excellent public transportation system operated by MVV, including U-Bahn (subway), S-Bahn (suburban trains), trams, and buses. Monthly passes (IsarCard) offer significant savings compared to individual tickets.",
        
        # German Courses
        "Learning German is crucial for integration. The Volkshochschule München (VHS) offers affordable language courses at all levels. Goethe-Institut provides more intensive but costlier options. Online platforms like Duolingo or Babbel can supplement formal learning.",
        
        # Housing
        "Finding accommodation in Munich is challenging due to high demand. Websites like ImmobilienScout24, WG-Gesucht, and Mr. Lodge are popular for apartment hunting. Expect to pay a deposit (Kaution) of 2-3 months' rent and possibly a commission fee (Provision) if using an agent.",
        
        # Integration Course
        "For non-EU citizens, integration courses (Integrationskurs) are often mandatory. These include language lessons and orientation modules about German culture, history, and legal system. The Federal Office for Migration and Refugees (BAMF) subsidizes these courses."
    ]
    
    # Create a simple in-memory vector store
    return Qdrant.from_texts(
        texts=texts,
        embedding=embeddings,
        location=":memory:",  # In-memory storage for this example
        collection_name="munich_relocation_kb"
    )

# Create a conversational chain with retrieval
def get_conversation_chain():
    llm = get_llm()
    vectorstore = get_knowledge_base()
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )
    
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        verbose=True
    )
    
    return chain

# For basic responses without knowledge retrieval
def get_basic_chain():
    llm = get_llm()
    
    template = """
    You are KI Kompass, an AI assistant specializing in helping people relocate to Munich, Germany.
    Be friendly, helpful, and provide concise information about relocation processes, requirements, and tips.
    
    User profile: {user_profile}
    
    User question: {query}
    
    Your response:
    """
    
    prompt = PromptTemplate(
        input_variables=["user_profile", "query"],
        template=template
    )
    
    chain = LLMChain(
        llm=llm, 
        prompt=prompt, 
        verbose=True
    )
    
    return chain
