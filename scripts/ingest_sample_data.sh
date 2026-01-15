#!/bin/bash
set -e

echo "=========================================="
echo "Ingesting Sample Arabic Documents"
echo "=========================================="

# Check if API is running
if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Error: API is not running at http://localhost:8000"
    echo "Please start the services first with: docker-compose up -d"
    exit 1
fi

echo ""
echo "📚 Ingesting geography data..."
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "القاهرة هي عاصمة جمهورية مصر العربية وأكبر مدنها. تقع على ضفاف نهر النيل في شمال مصر.",
      "الرياض هي عاصمة المملكة العربية السعودية وأكبر مدنها. تقع في قلب شبه الجزيرة العربية.",
      "بغداد هي عاصمة جمهورية العراق وأكبر مدنها. تقع على نهر دجلة.",
      "دمشق هي عاصمة الجمهورية العربية السورية وتعتبر من أقدم المدن المأهولة في العالم.",
      "بيروت هي عاصمة الجمهورية اللبنانية وأكبر مدنها. تقع على ساحل البحر الأبيض المتوسط."
    ],
    "metadatas": [
      {"source": "geography", "country": "Egypt", "category": "capitals"},
      {"source": "geography", "country": "Saudi Arabia", "category": "capitals"},
      {"source": "geography", "country": "Iraq", "category": "capitals"},
      {"source": "geography", "country": "Syria", "category": "capitals"},
      {"source": "geography", "country": "Lebanon", "category": "capitals"}
    ]
  }'

echo ""
echo ""
echo "🔬 Ingesting science data..."
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "الذكاء الاصطناعي هو قدرة الآلات على محاكاة القدرات البشرية في التعلم والتفكير.",
      "التعلم الآلي هو فرع من الذكاء الاصطناعي يركز على بناء أنظمة تتعلم من البيانات.",
      "الشبكات العصبية هي نماذج حاسوبية مستوحاة من طريقة عمل الدماغ البشري.",
      "معالجة اللغات الطبيعية تمكن الحواسيب من فهم وتحليل اللغة البشرية.",
      "الرؤية الحاسوبية هي مجال يمكن الحواسيب من فهم وتفسير الصور والفيديو."
    ],
    "metadatas": [
      {"source": "science", "domain": "AI", "category": "technology"},
      {"source": "science", "domain": "ML", "category": "technology"},
      {"source": "science", "domain": "Neural Networks", "category": "technology"},
      {"source": "science", "domain": "NLP", "category": "technology"},
      {"source": "science", "domain": "Computer Vision", "category": "technology"}
    ]
  }'

echo ""
echo ""
echo "📖 Ingesting history data..."
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "الحضارة المصرية القديمة من أقدم الحضارات في التاريخ البشري وقد ازدهرت على ضفاف نهر النيل.",
      "الخلافة العباسية كانت ثالث خلافة إسلامية وقد اتخذت من بغداد عاصمة لها.",
      "الأندلس كانت مركزًا للحضارة الإسلامية في أوروبا وشهدت ازدهارًا علميًا وثقافيًا كبيرًا.",
      "الثورة الصناعية بدأت في بريطانيا في القرن الثامن عشر وغيرت وجه العالم.",
      "عصر النهضة الأوروبية كان فترة ازدهار فني وعلمي في أوروبا."
    ],
    "metadatas": [
      {"source": "history", "period": "Ancient", "region": "Egypt"},
      {"source": "history", "period": "Medieval", "region": "Middle East"},
      {"source": "history", "period": "Medieval", "region": "Europe"},
      {"source": "history", "period": "Modern", "region": "Europe"},
      {"source": "history", "period": "Renaissance", "region": "Europe"}
    ]
  }'

echo ""
echo ""
echo "=========================================="
echo "✅ Sample data ingested successfully!"
echo "=========================================="
echo ""
echo "🧪 Test the chatbot:"
echo ""
echo "curl -X POST http://localhost:8000/chat \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"question\": \"ما هي عاصمة مصر؟\"}'"
echo ""
echo "Or visit: http://localhost:8000/docs"
echo ""
