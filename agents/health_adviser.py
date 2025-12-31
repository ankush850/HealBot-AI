import os
import logging
import traceback
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.exceptions import OutputParserException
from openai import RateLimitError, APIError

# Load environment variables
load_dotenv()


# Fix for Pydantic compatibility issue
try:
    from langchain_core.callbacks import Callbacks
    from langchain_core.caches import BaseCache
    from langchain_openai import ChatOpenAI
    # Rebuild the model to fix the Pydantic issue
    ChatOpenAI.model_rebuild()
except Exception as e:
    print(f"Error rebuilding ChatOpenAI model: {e}")
    # Alternative import approach
    import langchain_openai
    ChatOpenAI = langchain_openai.ChatOpenAI

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('health_adviser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RAGState(TypedDict):
    question: str
    documents: List[str]
    answer: str
    error_message: Optional[str]
    processing_timestamp: str
    retrieval_score: float
    confidence_level: str

class HealthAdviserConfig:
    """Configuration class for health adviser"""
    def __init__(self):
        # API Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("HEALTH_MODEL_NAME", "gpt-4o")
        self.temperature = float(os.getenv("HEALTH_MODEL_TEMPERATURE", "0"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.timeout_seconds = int(os.getenv("REQUEST_TIMEOUT", "30"))
        
        # Embedding Configuration
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.embedding_device = os.getenv("EMBEDDING_DEVICE", "cpu")
        
        # Vector Store Configuration
        self.faiss_index_path = os.getenv("FAISS_INDEX_PATH", "faiss_index")
        self.max_documents = int(os.getenv("MAX_RETRIEVED_DOCS", "5"))
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
        
        # Validate required environment variables
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Validate paths
        if not Path(self.faiss_index_path).exists():
            logger.warning(f"FAISS index path does not exist: {self.faiss_index_path}")

config = HealthAdviserConfig()

class HealthAdviserError(Exception):
    """Custom exception for health adviser errors"""
    pass

def initialize_llm() -> Any:
    """Initialize LLM with robust error handling"""
    try:
        llm = ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            request_timeout=config.timeout_seconds,
            max_retries=config.max_retries
        )
        logger.info(f"Initialized LLM with model: {config.model_name}")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise HealthAdviserError(f"LLM initialization failed: {e}")

def initialize_embeddings() -> HuggingFaceEmbeddings:
    """Initialize embeddings with comprehensive error handling"""
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=config.embedding_model,
            model_kwargs={'device': config.embedding_device},
            encode_kwargs={'normalize_embeddings': True}
        )
        logger.info(f"Initialized embeddings with model: {config.embedding_model}")
        return embeddings
    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {e}")
        raise HealthAdviserError(f"Embeddings initialization failed: {e}")

def initialize_vector_store(embeddings: HuggingFaceEmbeddings) -> Optional[FAISS]:
    """Initialize vector store with comprehensive error handling"""
    try:
        if not Path(config.faiss_index_path).exists():
            logger.error(f"FAISS index directory does not exist: {config.faiss_index_path}")
            return None
            
        vector_store = FAISS.load_local(
            config.faiss_index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Verify the vector store is functional
        test_results = vector_store.similarity_search("test query", k=1)
        logger.info(f"Vector store loaded successfully. Contains {vector_store.index.ntotal} documents")
        return vector_store
        
    except RuntimeError as e:
        logger.error(f"Runtime error loading FAISS index: {e}")
        logger.error("Please run `scripts/ingest_data.py` to create the FAISS index")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading vector store: {e}")
        return None

# Initialize components with error handling
try:
    llm = initialize_llm()
    embeddings = initialize_embeddings()
    vector_store = initialize_vector_store(embeddings)
    
    if vector_store is None:
        logger.warning("Vector store not available - operating in fallback mode")
        retriever = None
    else:
        retriever = vector_store.as_retriever(
            search_kwargs={"k": config.max_documents}
        )
        logger.info("Health adviser components initialized successfully")
        
except Exception as e:
    logger.error(f"Failed to initialize health adviser components: {e}")
    raise

def validate_question(question: str) -> bool:
    """Validate user question input"""
    if not question or not isinstance(question, str):
        return False
    
    # Check minimum length
    if len(question.strip()) < 3:
        return False
    
    # Check for obvious spam or inappropriate content
    spam_indicators = ['spam', 'advertisement', 'buy now', 'click here']
    question_lower = question.lower()
    if any(indicator in question_lower for indicator in spam_indicators):
        return False
    
    return True

def sanitize_question(question: str) -> str:
    """Sanitize user input"""
    # Remove excessive whitespace
    question = ' '.join(question.split())
    
    # Limit length to prevent abuse
    max_length = 500
    if len(question) > max_length:
        question = question[:max_length] + "..."
        logger.warning(f"Question truncated to {max_length} characters")
    
    return question.strip()

def calculate_retrieval_score(documents: List[str]) -> float:
    """Calculate a simple retrieval quality score"""
    if not documents:
        return 0.0
    
    # Simple heuristic based on document count and average length
    avg_length = sum(len(doc) for doc in documents) / len(documents)
    doc_count_score = min(len(documents) / config.max_documents, 1.0)
    length_score = min(avg_length / 200, 1.0)  # Assume 200 chars is good length
    
    return (doc_count_score + length_score) / 2

def determine_confidence_level(retrieval_score: float, doc_count: int) -> str:
    """Determine confidence level based on retrieval quality"""
    if retrieval_score > 0.7 and doc_count >= 3:
        return "High"
    elif retrieval_score > 0.5 and doc_count >= 2:
        return "Medium"
    elif retrieval_score > 0.3 and doc_count >= 1:
        return "Low"
    else:
        return "Very Low"

def retrieve_node(state: RAGState) -> RAGState:
    """Retrieve relevant documents with comprehensive error handling"""
    logger.info("Starting document retrieval")
    
    try:
        # Initialize default values
        state['documents'] = []
        state['retrieval_score'] = 0.0
        state['confidence_level'] = "Very Low"
        state['processing_timestamp'] = datetime.now().isoformat()
        
        question = state.get("question", "")
        
        # Validate and sanitize question
        if not validate_question(question):
            logger.warning(f"Invalid question provided: {question[:50]}...")
            state['error_message'] = "Please provide a valid health-related question."
            return state
        
        question = sanitize_question(question)
        state['question'] = question  # Update with sanitized version
        
        # Check if retriever is available
        if retriever is None:
            logger.error("Vector store retriever not available")
            state['error_message'] = "Document search service temporarily unavailable."
            return state
        
        # Perform retrieval with error handling
        try:
            retrieved_docs = retriever.invoke(question)
            
            if not retrieved_docs:
                logger.warning("No documents retrieved for question")
                state['documents'] = []
            else:
                # Filter documents by relevance and quality
                quality_docs = []
                for doc in retrieved_docs:
                    if hasattr(doc, 'page_content') and doc.page_content.strip():
                        # Filter out very short or low-quality documents
                        if len(doc.page_content.strip()) > 50:
                            quality_docs.append(doc.page_content.strip())
                
                state['documents'] = quality_docs[:config.max_documents]
                logger.info(f"Retrieved {len(state['documents'])} quality documents")
        
        except Exception as retrieval_error:
            logger.error(f"Error during document retrieval: {retrieval_error}")
            state['error_message'] = "Unable to search health database at this time."
            return state
        
        # Calculate retrieval metrics
        state['retrieval_score'] = calculate_retrieval_score(state['documents'])
        state['confidence_level'] = determine_confidence_level(
            state['retrieval_score'], 
            len(state['documents'])
        )
        
        logger.info(f"Retrieval completed - Score: {state['retrieval_score']:.2f}, "
                   f"Confidence: {state['confidence_level']}")
        
    except Exception as e:
        logger.error(f"Unexpected error in retrieve_node: {e}\n{traceback.format_exc()}")
        state['error_message'] = "An error occurred while searching for information."
        state['documents'] = []
    
    return state

def generate_node(state: RAGState) -> RAGState:
    """Generate answer with comprehensive error handling and safety checks"""
    logger.info("Starting answer generation")
    
    try:
        question = state.get("question", "")
        documents = state.get("documents", [])
        confidence_level = state.get("confidence_level", "Very Low")
        
        if not question:
            state['error_message'] = "No question provided for answer generation."
            state['answer'] = "Please provide a health-related question."
            return state
        
        # Enhanced prompt with safety considerations
        prompt = ChatPromptTemplate.from_template(
            """You are a helpful AI health adviser from the Government of India, operating in Warangal, Telangana.
            Your role is to provide accurate, safe, and helpful health information.
            
            IMPORTANT GUIDELINES:
            1. Use ONLY the provided context to answer questions
            2. If context is insufficient, clearly state limitations
            3. Always encourage consulting healthcare professionals
            4. Never provide specific medical diagnoses
            5. Be culturally sensitive and appropriate for Indian context
            6. Include relevant disclaimers about medical advice
            7. Focus on general health education and awareness
            
            SAFETY PROTOCOLS:
            - For emergency symptoms, advise immediate medical attention
            - For serious conditions, emphasize professional consultation
            - Avoid recommending specific medications or treatments
            - Include local emergency contact information when relevant
            
            Current Date: {current_date}
            Question Confidence Level: {confidence_level}
            Available Context Quality: {context_quality}
            
            CONTEXT DOCUMENTS:
            {context}
            
            USER QUESTION:
            {question}
            
            RESPONSE GUIDELINES:
            - Start with a brief, clear answer
            - Provide relevant health education if context allows
            - Include appropriate disclaimers
            - Suggest next steps (consulting doctor, preventive measures, etc.)
            - End with encouragement to seek professional help for specific concerns
            
            ANSWER:
            """
        )
        
        # Prepare context
        context_str = "\n\n---\n\n".join(documents) if documents else "No relevant documents found."
        context_quality = f"{len(documents)} documents retrieved with {confidence_level.lower()} confidence"
        
        # Generate response with error handling
        try:
            chain = prompt | llm
            
            result = chain.invoke({
                "context": context_str,
                "question": question,
                "current_date": datetime.now().strftime('%B %d, %Y'),
                "confidence_level": confidence_level,
                "context_quality": context_quality
            })
            
            # Validate and process the generated answer
            answer = result.content if hasattr(result, 'content') else str(result)
            
            if not answer or len(answer.strip()) < 10:
                logger.warning("Generated answer is too short or empty")
                answer = _generate_fallback_response(question, confidence_level)
            
            # Add confidence indicator and disclaimers
            enhanced_answer = _enhance_answer_with_metadata(answer, state)
            state['answer'] = enhanced_answer
            
            logger.info(f"Answer generated successfully (length: {len(answer)} chars)")
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            state['answer'] = _generate_rate_limit_response()
            state['error_message'] = "Service temporarily unavailable due to high demand."
            
        except APIError as e:
            logger.error(f"API error during generation: {e}")
            state['answer'] = _generate_api_error_response()
            state['error_message'] = "Unable to generate response due to service error."
            
        except OutputParserException as e:
            logger.error(f"Output parsing error: {e}")
            state['answer'] = _generate_fallback_response(question, confidence_level)
            state['error_message'] = "Error processing response format."
            
        except Exception as e:
            logger.error(f"Unexpected error during generation: {e}\n{traceback.format_exc()}")
            state['answer'] = _generate_fallback_response(question, confidence_level)
            state['error_message'] = "An unexpected error occurred during response generation."
    
    except Exception as e:
        logger.error(f"Critical error in generate_node: {e}\n{traceback.format_exc()}")
        state['answer'] = "I apologize, but I'm unable to process your question right now. Please try again later or consult a healthcare professional."
        state['error_message'] = "Critical system error occurred."
    
    return state

def _generate_fallback_response(question: str, confidence_level: str) -> str:
    """Generate a fallback response when primary generation fails"""
    return f"""I apologize, but I'm having difficulty processing your question about: "{question[:100]}..."

    **General Health Advice:**
    • For any health concerns, it's always best to consult with a qualified healthcare professional
    • If you're experiencing emergency symptoms, please contact emergency services immediately (108 in India)
    • For non-emergency health questions, consider visiting your local healthcare center
    
    **Local Resources in Warangal:**
    • Government Hospital Warangal
    • Primary Health Centers in your area
    • Consult your family doctor for personalized advice
    
    **Disclaimer:** This system provides general health information only and cannot replace professional medical advice.
    
    Please try rephrasing your question or consult a healthcare provider for specific medical concerns."""

def _generate_rate_limit_response() -> str:
    """Generate response for rate limit scenarios"""
    return """I apologize, but our service is experiencing high demand right now.
    
    **Please try:**
    • Waiting a few minutes before asking again
    • For urgent health concerns, contact a healthcare provider directly
    • Call 108 for medical emergencies
    
    **Alternative Resources:**
    • Government Health Helpline: 104
    • Local hospital emergency numbers
    • Visit your nearest Primary Health Center
    
    Thank you for your patience."""

def _generate_api_error_response() -> str:
    """Generate response for API errors"""
    return """I'm currently experiencing technical difficulties and cannot provide a detailed response.
    
    **For immediate health concerns:**
    • Contact your doctor or local healthcare provider
    • Visit the nearest hospital or clinic
    • Call 108 for emergencies
    
    **General health resources:**
    • Government of India Health Portal
    • Local health department information
    • Consult healthcare professionals for medical advice
    
    Please try again later when our services are restored."""

def _enhance_answer_with_metadata(answer: str, state: RAGState) -> str:
    """Enhance answer with confidence levels and additional metadata"""
    confidence = state.get('confidence_level', 'Unknown')
    doc_count = len(state.get('documents', []))
    
    # Add confidence indicator
    confidence_notice = ""
    if confidence == "Very Low" or doc_count == 0:
        confidence_notice = "\n\n⚠️ **Limited Information Available**: This response is based on limited context. Please consult a healthcare professional for reliable advice."
    elif confidence == "Low":
        confidence_notice = "\n\n📋 **General Information**: This response provides general health information. For specific medical advice, please consult a qualified healthcare professional."
    
    # Add standard disclaimers
    disclaimers = [
        "",
        "---",
        "**Important Disclaimers:**",
        "• This information is for educational purposes only",
        "• Not a substitute for professional medical advice",
        "• Always consult healthcare providers for medical concerns",
        "• In emergencies, call 108 or visit the nearest hospital",
        "",
        f"*Response generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} with {confidence.lower()} confidence based on {doc_count} reference documents.*"
    ]
    
    return answer + confidence_notice + "\n" + "\n".join(disclaimers)

def error_handler_node(state: RAGState) -> RAGState:
    """Handle errors gracefully with helpful information"""
    logger.error(f"Error handler activated: {state.get('error_message', 'Unknown error')}")
    
    error_response = [
        "⚠️ **Service Error**",
        "",
        "I apologize, but I encountered an issue while processing your health question.",
        "",
        "**What you can do:**",
        "• Try rephrasing your question and ask again",
        "• Wait a few minutes and retry",
        "• For urgent health matters, contact a healthcare provider directly",
        "",
        "**Emergency Resources:**",
        "• Emergency Services: 108",
        "• Health Helpline: 104",
        "• Local hospitals and clinics in Warangal",
        "",
        "**General Health Resources:**",
        "• Government Health Portal: www.mohfw.gov.in",
        "• Consult your family doctor for personalized advice",
        "• Visit your nearest Primary Health Center",
        "",
        "Thank you for your understanding."
    ]
    
    if state.get('error_message'):
        error_response.insert(2, f"Error details: {state['error_message']}")
    
    state['answer'] = "\n".join(error_response)
    return state

def create_health_adviser_workflow() -> StateGraph:
    """Create and configure the health adviser workflow"""
    try:
        workflow = StateGraph(RAGState)
        
        # Add nodes
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("generate", generate_node)
        workflow.add_node("error_handler", error_handler_node)
        
        # Configure edges
        workflow.set_entry_point("retrieve")
        
        # Add conditional edge to handle errors
        def decide_after_retrieval(state: RAGState) -> str:
            if state.get('error_message'):
                return "error_handler"
            return "generate"
        
        def decide_after_generation(state: RAGState) -> str:
            if state.get('error_message') and not state.get('answer'):
                return "error_handler"
            return END
        
        workflow.add_conditional_edges(
            "retrieve",
            decide_after_retrieval,
            {
                "generate": "generate",
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "generate",
            decide_after_generation,
            {
                "error_handler": "error_handler",
                END: END
            }
        )
        
        workflow.add_edge("error_handler", END)
        
        logger.info("Health adviser workflow created successfully")
        return workflow
        
    except Exception as e:
        logger.error(f"Failed to create health adviser workflow: {e}")
        raise

# Create the health adviser application
try:
    health_adviser_app = create_health_adviser_workflow().compile()
    logger.info("Health adviser initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize health adviser: {e}")
    raise

def test_health_adviser():
    """Test function for the health adviser"""
    try:
        test_questions = [
            "What are the symptoms of diabetes?",
            "How can I prevent heart disease?",
            "What should I do if I have a fever?"
        ]
        
        for question in test_questions:
            logger.info(f"Testing question: {question}")
            try:
                result = health_adviser_app.invoke({"question": question})
                logger.info(f"Test successful - Answer length: {len(result.get('answer', ''))}")
            except Exception as e:
                logger.error(f"Test failed for question '{question}': {e}")
                
    except Exception as e:
        logger.error(f"Health adviser test failed: {e}")

# Example usage and testing
if __name__ == "__main__":
    print("--- Enhanced Health Adviser Agent ---")
    print("Ask a health-related question. Type 'exit' to quit.")
    print("Type 'test' to run system tests.")
    
    while True:
        try:
            user_question = input("\nYOU: ").strip()
            
            if user_question.lower() == 'exit':
                print("Thank you for using the Health Adviser. Stay healthy!")
                break
            
            if user_question.lower() == 'test':
                test_health_adviser()
                continue
                
            if not user_question:
                print("Please enter a valid question.")
                continue
            
            logger.info(f"Processing user question: {user_question[:50]}...")
            
            inputs = {"question": user_question}
            final_state = health_adviser_app.invoke(inputs)
            
            print(f"\nHEALTH ADVISER:")
            print(final_state.get('answer', 'No answer generated'))
            
            # Show confidence level in debug mode
            if os.getenv('DEBUG') == 'true':
                confidence = final_state.get('confidence_level', 'Unknown')
                doc_count = len(final_state.get('documents', []))
                print(f"\n[Debug] Confidence: {confidence}, Documents: {doc_count}")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye! Stay healthy!")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print("An error occurred. Please try again.")