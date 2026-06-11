from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import text
from fastapi.responses import JSONResponse


router = APIRouter()

@router.get("/dashboard/{user_id}")
def get_dashboard(user_id: int, db: Session = Depends(get_db)):

    query = text("""
            SELECT  COUNT(DISTINCT i.id) AS total,COUNT(DISTINCT fe.candidate_id) AS evaluated,
    COUNT(DISTINCT i.id) - COUNT(DISTINCT fe.candidate_id) AS pending,
    COUNT(DISTINCT i.id) - COUNT(DISTINCT fe.candidate_id) AS in_progress
FROM public.interviews i JOIN public.panel_members pm  ON i.panel_id = pm.panel_id
LEFT JOIN public.final_evaluation fe  ON pm.user_id = fe.memberid AND i.candidate_id = fe.candidate_id
WHERE pm.user_id = :user_id
    """)

    result = db.execute(query, {"user_id": user_id}).fetchone()

    return {
        "total": result.total or 0,
        "evaluated": result.evaluated or 0,
        "pending": result.pending or 0,
        "in_progress": result.in_progress or 0
    }

# @router.get("/interviews/user/{user_id}")
# def get_interviews(user_id: int, db: Session = Depends(get_db)):

#     query = text("""
#         SELECT u.name, b.user_id, b.role,
#                a.id, a.candidate_id, a.panel_id,
#                a.scheduled_at, a.status
#         FROM interviews a
#         JOIN panel_members b ON a.panel_id = b.panel_id
#         JOIN users u ON u.id = b.user_id
#         WHERE b.user_id = :user_id
#     """)

#     result = db.execute(query, {"user_id": user_id})

#     data = []
#     for row in result:
#         data.append({
#             "name": row.name,
#             "user_id": row.user_id,
#             "role": row.role,
#             "interview_id": row.id,
#             "candidate_id": row.candidate_id,
#             "panel_id": row.panel_id,
#             "scheduled_at": str(row.scheduled_at),
#             "status": row.status
#         })

#     return data



@router.get("/interviews/user/{user_id}")
def get_interviews(user_id: int, db: Session = Depends(get_db)):

    query = text("""
        SELECT 
            u.name, 
            b.user_id, 
            b.role,
            a.id, 
            a.candidate_id, 
            a.panel_id,
            TO_CHAR(a.scheduled_at, 'DD Mon YYYY HH12:MI AM') AS scheduled_at,
            a.status
        FROM interviews a
        JOIN panel_members b ON a.panel_id = b.panel_id
        JOIN users u ON u.id = b.user_id
        WHERE b.user_id = :user_id
    """)

    result = db.execute(query, {"user_id": user_id})

    data = []
    for row in result:
        data.append({
            "name": row.name,
            "user_id": row.user_id,
            "role": row.role,
            "interview_id": row.id,
            "candidate_id": row.candidate_id,
            "panel_id": row.panel_id,
            "scheduled_at": row.scheduled_at,  # ✅ already formatted
            "status": row.status
        })

    return data



@router.get("/interviews/formatted/{user_id}")
def get_formatted_interviews(user_id: int, db: Session = Depends(get_db)):

    query = text("""
        SELECT  c.name,
            i.interview_id,
            i.interview_category,
            i.candidate_id,
            i.panel_id,
            i.status,
            TO_CHAR(i.scheduled_at::timestamp, 'DD Mon YYYY HH12:MI AM') AS scheduled_at,
            pm.role  
        FROM public.interviews i 
        JOIN public.panel_members pm ON i.panel_id = pm.panel_id
        JOIN public.candidates c ON c.id = i.candidate_id
        WHERE pm.user_id = :user_id
    """)

    result = db.execute(query, {"user_id": user_id})

    data = []
    for row in result:
        data.append({
             "candidate_name": row.name,
            "interview_id": row.interview_id,
            "interview_category": row.interview_category,
            "candidate_id": row.candidate_id,
            "panel_id": row.panel_id,
            "status": row.status,
            "scheduled_at": row.scheduled_at,  # ✅ already formatted
            "role": row.role
        })

    return data




@router.get("/member/interviews/{user_id}/{candidate_id}")
def get_member_interviews(
    user_id: int,
    candidate_id: int,
    db: Session = Depends(get_db)
):

    query = text("""
        SELECT 
            pm.panel_id, 
            pm.user_id, 
            pm.role,
            c.name, 
            i.candidate_id, 
            i.status
        FROM panel_members pm
        JOIN interviews i ON pm.panel_id = i.panel_id
        JOIN candidates c ON c.id = i.candidate_id
        WHERE pm.user_id = :user_id  
        AND i.candidate_id = :candidate_id
    """)

    result = db.execute(query, {
        "user_id": user_id,
        "candidate_id": candidate_id
    })

    data = []
    for row in result:
        data.append({
            "panel_id": row.panel_id,
            "user_id": row.user_id,
            "role": row.role,
            "candidate_name": row.name,
            "candidate_id": row.candidate_id,
            "status": row.status
        })

    return data



# @router.get("/candidate/{candidate_id}")
# def get_candidate(candidate_id: int, db: Session = Depends(get_db)):

#     query = text("""
#         SELECT
#             video_path AS recorded_video,
#               -- ✅ ADD THIS
#             resume_filename,
#             id,
#             name,

#             student_course_program,
#             student_department_branch,
#             student_university,
#             student_enrollment_no,

#             student_dob,
#             student_gender,
#             phone,
#             email,

#             student_cgpa,
#             student_category,
#             interview_id,
#             student_academic_year,
#             student_skills
#         FROM public.candidates
#         WHERE id = :candidate_id
#     """)

#     result = db.execute(query, {"candidate_id": candidate_id}).mappings().first()

#     if not result:
#         return {"message": "Candidate not found"}

#     return {
#         "id": result["id"],
#         "name": result["name"],

#         "student_course_program": result["student_course_program"],
#         "student_department_branch": result["student_department_branch"],
#         "student_university": result["student_university"],
#         "student_enrollment_no": result["student_enrollment_no"],

#         "dob": result["student_dob"],
#         "gen": result["student_gender"],
#         "mob": result["phone"],
#         "email": result["email"],

#         "cgpa": result["student_cgpa"],
#         "category": result["student_category"],
#         "interview_id": result["interview_id"],
#         "sem": result["student_academic_year"],

#         "skills": result["student_skills"].split(",") if result["student_skills"] else [],

#         "recordedVideo": result["recorded_video"],
#         # ✅ ADD THIS
#         "resumeUrl": result["resume_filename"]
#     }
@router.get("/candidate/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):

    query = text("""
         SELECT
           video_path AS recorded_video ,
           '' as resume_filename ,
            id,
            name,

          '' as   student_course_program,
           '' as  student_department_branch,
           '' as  student_university,
          '' as   student_enrollment_no,

          '' as   student_dob,
           '' as  student_gender,
            phone,
            email,
			course_program,
			department_branch,

           '' as  student_cgpa,
          '' as   student_category,
           '' as  interview_id,
          '' as   student_academic_year,
           '' as  student_skills
        FROM public.candidates
        WHERE id = :candidate_id
    """)

    result = db.execute(query, {"candidate_id": candidate_id}).mappings().first()

    if not result:
        return {"message": "Candidate not found"}

    return {
        "id": result["id"],
        "name": result["name"],

        "student_course_program": result["student_course_program"],
        "student_department_branch": result["student_department_branch"],
        "student_university": result["student_university"],
        "student_enrollment_no": result["student_enrollment_no"],

        "dob": result["student_dob"],
        "gen": result["student_gender"],
        "mob": result["phone"],
        "email": result["email"],

        "cgpa": result["student_cgpa"],
        "category": result["student_category"],
        "interview_id": result["interview_id"],
        "sem": result["student_academic_year"],

        "skills": result["student_skills"].split(",") if result["student_skills"] else [],

        "recordedVideo": result["recorded_video"],
        # ✅ ADD THIS
        "resumeUrl": result["resume_filename"]
    }


  
# @router.get("/qa-evaluation-log/{candidate_id}")
# def get_candidate_questionAndAnswer(candidate_id: int, db: Session = Depends(get_db)):

#     query = text("""
#         SELECT 
#             a.id AS answer_id,
#             a.candidate_id,
#             q.id AS question_id,
#             q.question_text,
#             q.expected_answer,
#             a.answer_text,
#             COALESCE(a.score, 0) AS score
#         FROM public.answers a 
#         JOIN public.question_bank q 
#             ON a.question_id = q.id
#         WHERE a.candidate_id::int = :candidate_id
#         ORDER BY a.id
#     """)

#     results = db.execute(query, {"candidate_id": candidate_id}).mappings().all()

#     if not results:
#         return {"message": "No Q&A found for this candidate"}

#     return {
#         "candidateId": candidate_id,
#         "qaList": [
#             {
#                 "question_id": row["question_id"],   # ✅ IMPORTANT
#                 "question": row["question_text"],
#                 "expectedAnswer": row["expected_answer"],
#                 "answer": row["answer_text"],
#                 "score": row["score"]
#             }
#             for row in results
#         ]
#     }


@router.get("/qa-evaluation-log/{candidate_id}/{member_id}")
def get_candidate_questionAndAnswer(
    candidate_id: int,
    member_id: int,
    db: Session = Depends(get_db)
):

    query = text("""
                 
select a.id AS answer_id, i.candidate_id, q.id AS question_id,q.question_text,q.expected_answer, a.answer_text,a.ai_response, a.ai_score,
   COALESCE(fe.score, 0) AS score
from public.interviews i join public.panel_members pm  ON i.panel_id = pm.panel_id
left join public.answers a on i.panel_id=a.panel_id  and i.candidate_id=a.candidate_id::int
join public.question_bank q  ON a.question_id = q.id
LEFT JOIN public.final_evaluation fe ON pm.user_id = fe.memberid 
AND i.candidate_id = fe.candidate_id AND q.id = fe.question_id   -- ✅ IMPORTANT FIX
where i.candidate_id=:candidate_id and pm.user_id = :member_id

  
    """)

    results = db.execute(query, {
        "candidate_id": candidate_id,
        "member_id": member_id
    }).mappings().all()

    if not results:
        return {"message": "No Q&A found for this candidate"}

    return {
        "candidateId": candidate_id,
        "memberId": member_id,
        "qaList": [
            {
                "question_id": row["question_id"],
                "question": row["question_text"],
                "expectedAnswer": row["expected_answer"],
                "answer": row["answer_text"],
                "score": row["score"],
                "ai_response": row["ai_response"],
                "ai_score": row["ai_score"]
            }
            for row in results
        ]
    }


    # ✅ MOVE HERE (OUTSIDE FUNCTION)

# @router.post("/final-evaluation")
# def save_final_evaluation(data: dict, db: Session = Depends(get_db)):

#     try:
#         print("🔥 Incoming Data:", data)

#         query = text("""
#             INSERT INTO public.final_evaluation
#             (candidate_id, memberid, question_id, score, remark, final_verdict, created_at)
#             VALUES
#             (:candidate_id, :memberid, :question_id, :score, :remark, :final_verdict, NOW())
#         """)

#         for item in data["qaList"]:
#             print("➡️ Inserting:", item)

#             db.execute(query, {
#                 "candidate_id": str(data["candidateId"]),  # ✅ FIX
#                 "memberid": data["memberId"],
#                 "question_id": item["question_id"],
#                 "score": item["score"],
#                 "remark": data["remark"],
#                 "final_verdict": data["verdict"]
#             })

#         db.commit()

#         print("✅ SAVED SUCCESSFULLY")
#         return {"message": "Saved successfully"}

#     except Exception as e:
#         db.rollback()
#         print("❌ ERROR:", str(e))
#         return {"error": str(e)}
 
 


@router.post("/final-evaluation")
def save_final_evaluation(data: dict, db: Session = Depends(get_db)):

    try:
        print("🔥 Incoming Data:", data)

        # =========================
        # 1️⃣ SAVE Q&A
        # =========================
        qa_query = text("""
            INSERT INTO public.final_evaluation
            (candidate_id, memberid, question_id, score, remark, final_verdict, created_at)
            VALUES
            (:candidate_id, :memberid, :question_id, :score, :remark, :final_verdict, NOW())
        """)

        for item in data["qaList"]:
            db.execute(qa_query, {
                "candidate_id": data["candidateId"],
                "memberid": data["memberId"],
                "question_id": item["question_id"],
                "score": item["score"],
                "remark": data["remark"],
                "final_verdict": data["verdict"]
            })

        # =========================
        # 2️⃣ SAVE FINAL MARKS
        # =========================
        final_query = text("""
            INSERT INTO public.final_mark_verdict (
                candidate_id,
                memberid,
                technical_knowledge,
                problem_solving,
                communication,
                domain_aptitude,
                overall_impression,
                remark,
                final_verdict,
                created_at
            )
            VALUES (
                :candidate_id,
                :memberid,
                :technical_knowledge,
                :problem_solving,
                :communication,
                :domain_aptitude,
                :overall_impression,
                :remark,
                :final_verdict,
                NOW()
            )
        """)

        db.execute(final_query, {
            "candidate_id": data["candidateId"],
            "memberid": data["memberId"],
            "technical_knowledge": data["technical_knowledge"],
            "problem_solving": data["problem_solving"],
            "communication": data["communication"],
            "domain_aptitude": data["domain_aptitude"],
            "overall_impression": data["overall_impression"],
            "remark": data["remark"],
            "final_verdict": data["verdict"]
        })

        # =========================
        # ✅ COMMIT
        # =========================
        db.commit()

        print("✅ RETURNING SUCCESS RESPONSE")

        return JSONResponse(
            status_code=200,
            content={"message": "Evaluation submitted successfully!"}
        )

    except Exception as e:
        db.rollback()
        print("❌ ERROR:", str(e))

        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )



# 🚀 API endpoint

# ✅ FINAL: Panel Members with Done/Pending Status
@router.get("/panel-members/{panel_id}")
def get_panel_members(panel_id: int, db: Session = Depends(get_db)):

    query = text("""
        SELECT 
            u.name,
            u.role AS user_role,
            u.designation,
            i.candidate_id,
            i.panel_id,
            p.user_id AS memberid,
            p.role AS panel_role,

            CASE 
                WHEN fe.id IS NOT NULL THEN 'Done' 
                ELSE 'Pending' 
            END AS status

        FROM public.interviews i

        JOIN public.panel_members p 
            ON i.panel_id = p.panel_id

        JOIN public.users u 
            ON p.user_id = u.id

        LEFT JOIN (
            SELECT DISTINCT ON (candidate_id, memberid) 
                   id, candidate_id, memberid
            FROM public.final_evaluation
            ORDER BY candidate_id, memberid, created_at DESC
        ) fe
        ON fe.candidate_id = i.candidate_id 
        AND fe.memberid = p.user_id

        WHERE p.panel_id = :panel_id
    """)

    result = db.execute(query, {"panel_id": panel_id})

    return [
        {
            "name": row.name,
            "user_role": row.user_role,
            "designation": row.designation,
            "candidate_id": row.candidate_id,
            "panel_id": row.panel_id,
            "memberid": row.memberid,
            "panel_role": row.panel_role,
            "status": row.status
        }
        for row in result
    ]





@router.get("/final-mark/{candidate_id}/{member_id}")
def get_final_mark_verdict(
    candidate_id: int,
    member_id: int,
    db: Session = Depends(get_db)
):

    query = text("""
        SELECT 
            id,
            candidate_id,
            memberid,
            technical_knowledge,
            problem_solving,
            communication,
            domain_aptitude,
            overall_impression,
            remark,
            final_verdict,
            created_at
        FROM public.final_mark_verdict
        WHERE candidate_id = :candidate_id
        AND memberid = :member_id
    """)

    result = db.execute(query, {
        "candidate_id": candidate_id,
        "member_id": member_id
    }).mappings().first()   # 👈 single row expected

    if not result:
        return {"message": "No record found"}

    return {
        "id": result["id"],
        "candidate_id": result["candidate_id"],
        "memberid": result["memberid"],

        "technical_knowledge": result["technical_knowledge"],
        "problem_solving": result["problem_solving"],
        "communication": result["communication"],
        "domain_aptitude": result["domain_aptitude"],
        "overall_impression": result["overall_impression"],

        "remark": result["remark"],
        "final_verdict": result["final_verdict"],
        "created_at": str(result["created_at"])
    }





@router.get("/panel-question-scores/{panel_id}")
def get_panel_question_scores(panel_id: int, db: Session = Depends(get_db)):

    query = text("""
        SELECT 
            q.id AS question_id,
            q.question_text,
            q.expected_answer,
            a.answer_text,
            u.name AS member_name,
            COALESCE(fe.score, 0) AS score

        FROM public.interviews i

        JOIN public.panel_members pm  
            ON i.panel_id = pm.panel_id

        JOIN public.users u  
            ON pm.user_id = u.id

        LEFT JOIN public.answers a   
            ON i.candidate_id = a.candidate_id::int  

        JOIN public.question_bank q   
            ON a.question_id = q.id

        LEFT JOIN public.final_evaluation fe  
            ON pm.user_id = fe.memberid 
            AND i.candidate_id = fe.candidate_id 
            AND q.id = fe.question_id

        WHERE i.panel_id = :panel_id

        ORDER BY q.id, pm.user_id
    """)

    rows = db.execute(query, {"panel_id": panel_id}).mappings().all()

    # ✅ GROUP DATA (IMPORTANT)
    grouped = {}

    for row in rows:
        qid = row["question_id"]

        if qid not in grouped:
            grouped[qid] = {
                "question_id": qid,
                "question": row["question_text"],
                "expectedAnswer": row["expected_answer"],
                "answer": row["answer_text"],
                "members": []
            }

        grouped[qid]["members"].append({
            "name": row["member_name"],
            "score": row["score"]
        })

    return list(grouped.values())



@router.get("/panel-evaluation-final-mark/{panel_id}")
def get_panel_evaluation(panel_id: int, db: Session = Depends(get_db)):

    query = text("""
        SELECT 
            u.name,
            i.panel_id,
            i.candidate_id,
            pm.user_id,

            COALESCE(fmv.technical_knowledge, 0) AS technical_knowledge,
            COALESCE(fmv.problem_solving, 0) AS problem_solving,
            COALESCE(fmv.communication, 0) AS communication,
            COALESCE(fmv.domain_aptitude, 0) AS domain_aptitude,
            COALESCE(fmv.overall_impression, 0) AS overall_impression,

            COALESCE(fmv.remark, '') AS remark,
            COALESCE(fmv.final_verdict, 'Pending') AS final_verdict

        FROM public.interviews i

        JOIN public.panel_members pm 
            ON i.panel_id = pm.panel_id

        JOIN public.users u 
            ON pm.user_id = u.id

        LEFT JOIN public.final_mark_verdict fmv 
            ON i.candidate_id = fmv.candidate_id
            AND pm.user_id = fmv.memberid

        WHERE i.panel_id = :panel_id
    """)

    results = db.execute(query, {"panel_id": panel_id}).mappings().all()

    if not results:
        return {"message": "No records found"}

    # ✅ convert to list of dict
    data = []
    for row in results:
        data.append({
            "name": row["name"],
            "panel_id": row["panel_id"],
            "candidate_id": row["candidate_id"],
            "user_id": row["user_id"],

            "technical_knowledge": row["technical_knowledge"],
            "problem_solving": row["problem_solving"],
            "communication": row["communication"],
            "domain_aptitude": row["domain_aptitude"],
            "overall_impression": row["overall_impression"],

            "remark": row["remark"],
            "final_verdict": row["final_verdict"]
        })

    return data


@router.get("/final-remark/{candidate_id}/{member_id}")
def get_final_remark(
    candidate_id: int,
    member_id: int,
    db: Session = Depends(get_db)
):

    query = text("""
        SELECT DISTINCT remark
        FROM public.final_mark_verdict
        WHERE candidate_id = :candidate_id
        AND memberid = :member_id
    """)

    results = db.execute(query, {
        "candidate_id": candidate_id,
        "member_id": member_id
    }).fetchall()

    # ✅ If no data
    if not results:
        return {"remark": None}

    # ✅ Convert to list (same as your verdict API)
    remarks = [row[0] for row in results]

    return {
        "candidate_id": candidate_id,
        "member_id": member_id,
        "remark": remarks   # list
    }