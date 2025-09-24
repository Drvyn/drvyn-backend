from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime
from typing import List
from pydantic import BaseModel
from app.database.connection import db 

router = APIRouter()

class BlogPost(BaseModel):
    title: str
    content: str
    excerpt: str
    author: str
    authorRole: str
    image: str
    readTime: str

class BlogPostResponse(BlogPost):
    id: str
    date: str
    slug: str

@router.get("/api/blog", response_model=List[BlogPostResponse])
async def get_blog_posts():
    try:
        # Use your existing database connection
        posts = list(db.blog_posts.find({}).sort("date", -1))
        for post in posts:
            post["id"] = str(post["_id"])
            post["slug"] = post.get("slug", post["title"].lower().replace(" ", "-"))
        return posts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/blog/{slug}", response_model=BlogPostResponse)
async def get_blog_post(slug: str):
    try:
        post = db.blog_posts.find_one({"slug": slug})
        if not post:
            raise HTTPException(status_code=404, detail="Blog post not found")
        post["id"] = str(post["_id"])
        return post
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/blog", response_model=dict)
async def create_blog_post(post: BlogPost):
    try:
        post_data = post.dict()
        post_data["date"] = datetime.now().strftime("%B %d, %Y")
        post_data["slug"] = post_data["title"].lower().replace(" ", "-")
        
        result = db.blog_posts.insert_one(post_data)
        return {"id": str(result.inserted_id), "message": "Blog post created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))