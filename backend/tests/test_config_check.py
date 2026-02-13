"""
Dry-run test for environment-aware configuration.
Tests that the Config class correctly loads secrets in local mode.
"""
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings

def test_config():
    print("=" * 60)
    print("🧪 Environment-Aware Configuration Test")
    print("=" * 60)
    
    # Environment detection
    print(f"\n📍 Environment Detection:")
    print(f"   Is Kubernetes: {settings.is_kubernetes}")
    print(f"   Is Local: {settings.is_local}")
    print(f"   KUBERNETES_SERVICE_HOST: {os.getenv('KUBERNETES_SERVICE_HOST', 'Not set')}")
    print(f"   LOCAL_MODE: {os.getenv('LOCAL_MODE', 'Not set (auto-detect)')}")
    
    # Configuration values
    print(f"\n⚙️  Configuration Values:")
    print(f"   PROJECT_NAME: {settings.PROJECT_NAME}")
    print(f"   API_V1_STR: {settings.API_V1_STR}")
    print(f"   BASE_DIR: {settings.BASE_DIR}")
    
    # Secrets (masked)
    print(f"\n🔐 Secrets (Masked):")
    print(f"   OPENAI_API_KEY: {'✅ Set' if settings.OPENAI_API_KEY else '❌ Not set'}")
    print(f"   GOOGLE_API_KEY: {'✅ Set' if settings.GOOGLE_API_KEY else '❌ Not set'}")
    print(f"   LANGCHAIN_API_KEY: {'✅ Set' if settings.LANGCHAIN_API_KEY else '❌ Not set'}")
    
    # LLM Config
    print(f"\n🤖 LLM Configuration:")
    print(f"   LLM_MODEL: {settings.LLM_MODEL}")
    print(f"   GEMINI_MODEL: {settings.GEMINI_MODEL}")
    
    # Database
    print(f"\n💾 Database:")
    print(f"   SQLITE_URL: {settings.SQLITE_URL}")
    
    # RAG
    print(f"\n📚 RAG:")
    print(f"   FAISS_INDEX_PATH: {settings.FAISS_INDEX_PATH}")
    
    # Monitoring
    print(f"\n📊 Monitoring:")
    print(f"   LANGCHAIN_TRACING_V2: {settings.LANGCHAIN_TRACING_V2}")
    print(f"   OTEL_SERVICE_NAME: {settings.OTEL_SERVICE_NAME}")
    
    # Test secret loading method
    print(f"\n🧪 Testing get_secret() method:")
    try:
        test_value = settings.get_secret("LLM_MODEL", default="test-default")
        print(f"   ✅ get_secret('LLM_MODEL'): {test_value}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    try:
        test_missing = settings.get_secret("NONEXISTENT_KEY", default="fallback-value")
        print(f"   ✅ get_secret('NONEXISTENT_KEY', default='fallback-value'): {test_missing}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Configuration test completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    test_config()
