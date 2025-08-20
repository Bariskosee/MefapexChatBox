#!/bin/bash

# 🚀 MEFAPEX Database Optimization Quick Start
# ============================================

echo "🚀 MEFAPEX Database Optimization Suite"
echo "======================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL connection..."
python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'mefapex_chatbot'),
        user=os.getenv('POSTGRES_USER', 'mefapex'),
        password=os.getenv('POSTGRES_PASSWORD', 'mefapex')
    )
    conn.close()
    print('✅ PostgreSQL connection successful')
except Exception as e:
    print(f'❌ PostgreSQL connection failed: {e}')
    print('Please ensure PostgreSQL is running:')
    print('  docker-compose up postgres')
    exit(1)
" || exit 1

# Run optimization based on argument
case "${1:-full}" in
    "optimize")
        echo "🔧 Running database optimization only..."
        python run_database_optimization.py --action optimize --verbose
        ;;
    "monitor")
        echo "📊 Setting up monitoring only..."
        python run_database_optimization.py --action monitor --verbose
        ;;
    "report")
        echo "📈 Generating health report only..."
        python run_database_optimization.py --action report --verbose --output "health_report_$(date +%Y%m%d_%H%M%S).json"
        ;;
    "validate")
        echo "🔍 Validating optimization only..."
        python run_database_optimization.py --action validate --verbose
        ;;
    "full"|*)
        echo "🚀 Running complete optimization suite..."
        python run_database_optimization.py --action full --verbose --output "optimization_report_$(date +%Y%m%d_%H%M%S).json"
        ;;
esac

echo ""
echo "🎉 Database optimization completed!"
echo "📊 Check the logs and reports for detailed results"
echo ""
echo "Available commands:"
echo "  ./optimize_database.sh optimize  - Run optimization only"
echo "  ./optimize_database.sh monitor   - Setup monitoring only"
echo "  ./optimize_database.sh report    - Generate report only"
echo "  ./optimize_database.sh validate  - Validate optimization"
echo "  ./optimize_database.sh full      - Complete suite (default)"
