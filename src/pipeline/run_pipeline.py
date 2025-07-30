import os
from dotenv import load_dotenv
from src.pipeline.document_loader import load_and_clean
from src.pipeline.splitter import chunk_text, smart_chunk_text
from src.pipeline.embedder import embed_and_store
from src.pipeline.retriever import retrieve_similar_chunks
from src.pipeline.formatter import format_context_and_query
import re
from collections import Counter

load_dotenv()

def process_file(file_bytes: bytes, filename: str, questions: list = None):
    """
    Process a file and return answers to questions.
    Fixed: Proper error handling and correct function signatures
    """
    if questions is None:
        questions = ["What is this document about?"]
    
    try:
        print(f"📄 Processing file: {filename}")
        
        # Step 1: Load and clean document
        print("📖 Extracting text from document...")
        document = load_and_clean(file_bytes, filename)
        
        if not document or not document.strip():
            raise ValueError("No text could be extracted from the document")
        
        print(f"✅ Extracted {len(document)} characters")
        
        # Step 2: Chunk the document
        print("🔪 Chunking document...")
        # Use smart chunking for better results
        chunks = smart_chunk_text(document, source_filename=filename)
        
        if not chunks:
            raise ValueError("No chunks generated from document. Document might be too short or empty.")
        
        print(f"✅ Created {len(chunks)} chunks")
        
        # Step 3: Embed and store in Pinecone
        print("🧠 Embedding and storing chunks...")
        embed_and_store(chunks)
        
        # Step 4: Process each question
        answers = []
        for i, question in enumerate(questions):
            print(f"❓ Processing question {i+1}/{len(questions)}: {question}")
            
            # Retrieve relevant chunks
            results = retrieve_similar_chunks(question, top_k=5)
            
            if not results:
                print(f"⚠️ No relevant chunks found for question: {question}")
                answers.append("I couldn't find relevant information to answer this question.")
                continue
            
            # Generate answer from context
            answer = generate_improved_answer(results, question, document)
            answers.append(answer)
            
            print(f"✅ Generated answer for question {i+1}")
        
        return {
            "success": True,
            "answers": answers,
            "metadata": {
                "filename": filename,
                "chunks_created": len(chunks),
                "questions_processed": len(questions),
                "document_length": len(document)
            }
        }

    except Exception as e:
        print(f"❌ Error processing file {filename}: {e}")
        return {
            "success": False,
            "error": str(e),
            "answers": []
        }

def generate_improved_answer(retrieved_chunks, question, full_document=None):
    """
    Generate a comprehensive answer based on retrieved context and question analysis.
    """
    if not retrieved_chunks:
        return "I couldn't find relevant information to answer this question."
    
    # Combine the most relevant chunks
    context_texts = []
    for chunk in retrieved_chunks[:5]:  # Use top 5 chunks
        if chunk.get("text") and chunk.get("score", 0) > 0.3:  # Filter by relevance score
            context_texts.append(chunk["text"])
    
    if not context_texts:
        return "I couldn't find sufficiently relevant information to answer this question."
    
    combined_context = "\n\n".join(context_texts)
    question_lower = question.lower()
    
    # Analyze question type and generate appropriate answer
    if any(word in question_lower for word in ["what", "about", "describe", "explain"]):
        return analyze_document_content(combined_context, full_document)
    
    elif any(word in question_lower for word in ["who", "responsible", "person", "company", "organization"]):
        return extract_entities_and_roles(combined_context)
    
    elif any(word in question_lower for word in ["date", "when", "time", "period", "year"]):
        return extract_dates_and_periods(combined_context)
    
    elif any(word in question_lower for word in ["how much", "amount", "cost", "price", "fee", "premium"]):
        return extract_financial_information(combined_context)
    
    elif any(word in question_lower for word in ["coverage", "benefit", "include", "cover"]):
        return extract_coverage_information(combined_context)
    
    elif any(word in question_lower for word in ["exclude", "not cover", "limitation", "restriction"]):
        return extract_exclusions(combined_context)
    
    else:
        # General answer
        return f"Based on the document content: {combined_context[:500]}{'...' if len(combined_context) > 500 else ''}"

def analyze_document_content(context, full_document=None):
    """Analyze what the document is about"""
    # Look for document type indicators
    doc_type_indicators = {
        "policy": ["policy", "insurance", "coverage", "premium", "claim"],
        "medical": ["medical", "health", "hospital", "treatment", "illness"],
        "legal": ["agreement", "contract", "terms", "conditions", "obligations"],
        "financial": ["payment", "cost", "amount", "fee", "charges"]
    }
    
    context_lower = context.lower()
    doc_types = []
    
    for doc_type, keywords in doc_type_indicators.items():
        if sum(1 for keyword in keywords if keyword in context_lower) >= 2:
            doc_types.append(doc_type)
    
    # Extract key information
    key_info = []
    
    # Look for policy names or document titles
    title_patterns = [
        r'([A-Z][A-Za-z\s]+Policy)',
        r'([A-Z][A-Za-z\s]+Agreement)',
        r'([A-Z][A-Za-z\s]+Contract)',
        r'([A-Z][A-Za-z\s]+Plan)'
    ]
    
    for pattern in title_patterns:
        matches = re.findall(pattern, context)
        if matches:
            key_info.extend(matches[:3])  # Take first 3 matches
    
    # Build answer
    if key_info:
        answer = f"This document is a {', '.join(key_info)}."
    elif doc_types:
        answer = f"This appears to be a {' and '.join(doc_types)} document."
    else:
        answer = "This document contains"
    
    # Add main topics
    main_topics = extract_main_topics(context)
    if main_topics:
        answer += f" It covers topics including: {', '.join(main_topics[:5])}."
    
    return answer

def extract_entities_and_roles(context):
    """Extract people, companies, and roles from context"""
    entities = []
    
    # Company patterns
    company_patterns = [
        r'([A-Z][A-Za-z\s]+(?:Company|Corp|Corporation|Ltd|Limited|Inc|Insurance))',
        r'([A-Z][A-Za-z\s]+(?:Bank|Agency|Organization))'
    ]
    
    # Person/role patterns
    role_patterns = [
        r'(Proposer|Insured|Policy[- ]?holder|Beneficiary)',
        r'([A-Z][a-z]+\s[A-Z][a-z]+)',  # Names like "John Smith"
        r'(Medical Practitioner|Doctor|Physician)'
    ]
    
    for pattern in company_patterns + role_patterns:
        matches = re.findall(pattern, context, re.IGNORECASE)
        entities.extend([match.strip() for match in matches if len(match.strip()) > 2])
    
    # Remove duplicates and limit results
    unique_entities = list(dict.fromkeys(entities))[:10]
    
    if unique_entities:
        return f"Key entities mentioned: {', '.join(unique_entities)}"
    else:
        return "No specific entities or responsible parties clearly identified in the available context."

def extract_dates_and_periods(context):
    """Extract dates, periods, and time-related information"""
    dates = []
    periods = []
    
    # Date patterns
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DD/MM/YYYY or MM/DD/YYYY
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY/MM/DD
        r'\b[A-Za-z]+ \d{1,2}, \d{4}\b',       # Month DD, YYYY
        r'\b\d{1,2} [A-Za-z]+ \d{4}\b'         # DD Month YYYY
    ]
    
    # Period patterns
    period_patterns = [
        r'(\d+\s*(?:days?|months?|years?))',
        r'(Policy Period|Policy Year)',
        r'(grace period|waiting period)',
        r'(forty five days|45 days)',
        r'(annual|yearly|monthly|daily)'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, context)
        dates.extend(matches)
    
    for pattern in period_patterns:
        matches = re.findall(pattern, context, re.IGNORECASE)
        periods.extend(matches)
    
    result_parts = []
    if dates:
        result_parts.append(f"Dates mentioned: {', '.join(set(dates)[:5])}")
    if periods:
        result_parts.append(f"Time periods: {', '.join(set(periods)[:5])}")
    
    if result_parts:
        return ". ".join(result_parts)
    else:
        return "No specific dates or time periods clearly identified in the available context."

def extract_financial_information(context):
    """Extract costs, amounts, and financial information"""
    financial_info = []
    
    # Amount patterns
    amount_patterns = [
        r'₹\s*[\d,]+(?:\.\d+)?',  # Indian Rupees
        r'\$\s*[\d,]+(?:\.\d+)?',  # USD
        r'(?:Rs\.?|INR)\s*[\d,]+(?:\.\d+)?',  # Rupees
        r'premium.*?₹\s*[\d,]+',
        r'sum insured.*?₹\s*[\d,]+'
    ]
    
    for pattern in amount_patterns:
        matches = re.findall(pattern, context, re.IGNORECASE)
        financial_info.extend(matches)
    
    # Financial terms
    financial_terms = [
        'premium', 'deductible', 'co-payment', 'sum insured', 
        'coverage limit', 'floater sum', 'charges'
    ]
    
    found_terms = [term for term in financial_terms if term in context.lower()]
    
    result_parts = []
    if financial_info:
        result_parts.append(f"Financial amounts: {', '.join(set(financial_info)[:5])}")
    if found_terms:
        result_parts.append(f"Financial terms: {', '.join(found_terms[:5])}")
    
    if result_parts:
        return ". ".join(result_parts)
    else:
        return "No specific financial information clearly identified in the available context."

def extract_coverage_information(context):
    """Extract coverage and benefits information"""
    coverage_items = []
    
    # Coverage patterns
    coverage_patterns = [
        r'(hospitalisation|hospitalization)',
        r'(in-patient care|out-patient care)',
        r'(day care treatment|domiciliary)',
        r'(AYUSH treatment|ayurveda|homeopathy)',
        r'(medical advice|medical practitioner)',
        r'(illness|disease|injury|accident)'
    ]
    
    for pattern in coverage_patterns:
        if re.search(pattern, context, re.IGNORECASE):
            matches = re.findall(pattern, context, re.IGNORECASE)
            coverage_items.extend(matches)
    
    # Look for specific benefits
    benefit_keywords = [
        'indemnify', 'coverage', 'benefits', 'treatment', 
        'medical expenses', 'reasonable charges', 'customary charges'
    ]
    
    found_benefits = [keyword for keyword in benefit_keywords if keyword in context.lower()]
    
    if coverage_items or found_benefits:
        all_items = list(set(coverage_items + found_benefits))
        return f"Coverage includes: {', '.join(all_items[:8])}"
    else:
        return "Coverage details not clearly specified in the available context."

def extract_exclusions(context):
    """Extract exclusions and limitations"""
    exclusions = []
    
    # Look for exclusion keywords
    exclusion_patterns = [
        r'(not covered|excluded|limitation|restriction)',
        r'(subject to.*?exclusions)',
        r'(does not include|shall not)',
        r'(except|excluding|other than)'
    ]
    
    for pattern in exclusion_patterns:
        matches = re.findall(pattern, context, re.IGNORECASE)
        exclusions.extend(matches)
    
    if exclusions:
        return f"Limitations/exclusions mentioned: {', '.join(set(exclusions)[:5])}"
    else:
        return "No specific exclusions clearly identified in the available context."

def extract_main_topics(context):
    """Extract main topics from context using keyword frequency"""
    # Common words to ignore
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'this', 'that', 'these', 'those', 'such', 'any', 'all', 'each', 'every', 'some', 'many', 'much', 'more', 'most', 'other', 'another', 'same', 'different', 'new', 'old', 'first', 'last', 'good', 'great', 'small', 'large', 'big', 'little', 'long', 'short', 'high', 'low', 'right', 'left', 'next', 'previous', 'following', 'above', 'below', 'here', 'there', 'where', 'when', 'why', 'how', 'what', 'who', 'which', 'whose', 'whom'}
    
    # Extract words and count frequency
    words = re.findall(r'\b[A-Za-z]{3,}\b', context.lower())
    word_freq = Counter([word for word in words if word not in stop_words])
    
    # Get most common meaningful words
    common_words = [word for word, freq in word_freq.most_common(10) if freq > 1]
    
    return common_words[:5]

def process_multiple_files(file_data_list: list):
    """
    Process multiple files at once.
    file_data_list: List of tuples (file_bytes, filename)
    """
    results = []
    
    for file_bytes, filename in file_data_list:
        result = process_file(file_bytes, filename)
        results.append({
            "filename": filename,
            **result
        })
    
    return results

# CLI entrypoint for testing
def main():
    """CLI mode for testing the pipeline"""
    print("🚀 [CLI MODE] Loading documents from ./data ...")

    data_dir = "./data"
    if not os.path.exists(data_dir):
        print(f"❌ Directory {data_dir} not found.")
        print("Creating sample data directory...")
        os.makedirs(data_dir, exist_ok=True)
        print(f"📁 Created {data_dir}. Please add your documents there.")
        return

    # Improved questions for insurance documents
    test_questions = [
        "What is this document about?",
        "Who is responsible or involved in this policy?",
        "What are the key dates and time periods mentioned?",
        "What coverage and benefits are provided?",
        "What are the main exclusions or limitations?"
    ]

    files_processed = 0
    for fname in os.listdir(data_dir):
        file_path = os.path.join(data_dir, fname)
        if os.path.isfile(file_path) and not fname.startswith('.'):
            print(f"\n{'='*50}")
            print(f"Processing: {fname}")
            print('='*50)
            
            try:
                with open(file_path, "rb") as f:
                    result = process_file(f.read(), fname, test_questions)
                
                if result["success"]:
                    print(f"\n✅ Successfully processed {fname}")
                    print(f"📊 Metadata: {result['metadata']}")
                    
                    print(f"\n📝 Detailed Answers:")
                    for i, (question, answer) in enumerate(zip(test_questions, result["answers"])):
                        print(f"\n{'='*30}")
                        print(f"Q{i+1}: {question}")
                        print(f"{'='*30}")
                        print(f"A{i+1}: {answer}")
                else:
                    print(f"❌ Failed to process {fname}: {result['error']}")
                
                files_processed += 1
                
            except Exception as e:
                print(f"⚠️ Skipping {fname}: {e}")
    
    if files_processed == 0:
        print(f"\n⚠️ No files found in {data_dir}")
        print("Supported formats: PDF, DOCX, EML, MSG, PNG, JPG, JPEG, TXT")
    else:
        print(f"\n🎉 Processed {files_processed} files successfully!")

def test_with_insurance_text():
    """Test the pipeline with the provided insurance text"""
    insurance_text = """National Parivar Mediclaim Plus Policy
Whereas the Proposer designated in the schedule hereto has by a Proposal together with Declaration, which shall be the basis of
this contract and is deemed to be incorporated herein, has applied to National Insurance Company Ltd. (hereinafter called the
Company), for the insurance hereinafter set forth, in respect of person(s)/ family members named in the schedule hereto
(hereinafter called the Insured Persons) and has paid the premium as consideration for such insurance.
1 PREAMBLE
The Company undertakes that if during the Policy Period, any Insured Person shall suffer any illness or disease (hereinafter called
Illness) or sustain any bodily injury due to an Accident (hereinafter called Injury) requiring Hospitalisation of such Insured
Person(s) for In-Patient Care at any hospital/nursing home (hereinafter called Hospital) or for Day Care Treatment at any Day
Care Center or to undergo treatment under Domiciliary Hospitalisation, following the Medical Advice of a duly qualified Medical
Practitioner, the Company shall indemnify the Hospital or the Insured, Reasonable and Customary Charges incurred for Medically
Necessary Treatment towards the Coverage mentioned herein.
"""
    
    print("🧪 Testing pipeline with insurance document...")
    
    # Convert text to bytes
    sample_bytes = insurance_text.encode('utf-8')
    
    # Test questions specific to insurance document
    test_questions = [
        "What is this document about?",
        "Who is responsible or involved in this policy?",
        "What are the key dates and time periods mentioned?",
        "What coverage does this policy provide?"
    ]
    
    result = process_file(sample_bytes, "insurance_policy.txt", test_questions)
    
    if result["success"]:
        print("✅ Insurance document test successful!")
        for i, (question, answer) in enumerate(zip(test_questions, result["answers"])):
            print(f"\n{'='*40}")
            print(f"Q{i+1}: {question}")
            print(f"{'='*40}")
            print(f"A{i+1}: {answer}")
    else:
        print(f"❌ Insurance document test failed: {result['error']}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_with_insurance_text()
    else:
        main()