from model import User, Post
from orm.model import BaseDao

DB_URL = "main.db"
DB_MEMORY = ":memory:"
if __name__ == "__main__":
    print('App started')

    BaseDao.set_database(DB_MEMORY)
    BaseDao.set_module("model")
    BaseDao.create_table(User)
    BaseDao.create_table(Post)

    user1 = User()
    user1.name = "Ashwin"
    user1.user_id = 100
    user1.subject_id = 360
    BaseDao.save(User, user1)
    print(f'Added user {user1.name}')

    user2 = User()
    user2.name = "Kukku"
    user2.user_id = 100
    user2.subject_id = 360
    BaseDao.save(User, user2)
    print(f'Added user {user2.name}')

    post1 = Post()
    post1.title = "Post 1"
    post1.user_id = user1.id
    BaseDao.save(Post, post1)
    print(f'Added post {post1.title}')

    post2 = Post()
    post2.title = "Post 2"
    post2.user_id = user1.id
    BaseDao.save(Post, post2)
    print(f'Added post {post2.title}')

    user = BaseDao.get_by_id(User, 1)
    print(f"Get user by id = 1; User: {user.name}")

    query_builder = BaseDao.query_builder(User).select("*").where(name="Kukku").build()
    users = BaseDao.execute_query(query_builder, lazyload=True)
    print(f"Get user by name = Kukku; User: {users[0].id}")

    users = BaseDao.all(User)
    print(f"Get all users and posts")
    for user in users:
        print(f"> User: {user.name}")
        for post in user.posts:
            print(f">  Post: {post.title}")

    # query_builder = BaseDao.query_builder(User).select("*")._eq('name', 'Kukku')._or()._eq('name', 'Ashwin').build()
    # query_builder = BaseDao.query_builder(User).select("*")._gt('id', '1')._and()._eq('name', 'Kukku').build()
    # query_builder_names = BaseDao.query_builder(User).select("name").build()
    # query_builder = BaseDao.query_builder(User).select("*")._in('name', query_builder_names).build()
    query_builder = BaseDao.query_builder(User).select("*")._in('name', ['Ashwin', 'Kukku']).build()
    users = BaseDao.execute_query(query_builder, lazyload=False)
    print(f"Get users by name = Ashwin AND Kukku")
    for user in users:
        print(f"> User: {user.name}")
        for post in user.posts:
            print(f">  Post: {post.title}")

    # update_builder = BaseDao.update_builder(Post).set(title="Post Edited 1").where(title="Post 1").build()
    update_builder = BaseDao.update_builder(Post).set(title="Post Edited 1")._eq("title", "Post 1")._and()._eq('id', '1').build()
    BaseDao.execute_query(update_builder, lazyload=True)
    users = BaseDao.all(User)
    print(f"Get all users and posts after update")
    for user in users:
        print(f"> User: {user.name}")
        for post in user.posts:
            print(f">  Post: {post.title}")

    # delete_builder = BaseDao.delete_builder(Post).where(title="Post 2").build()
    delete_builder = BaseDao.delete_builder(Post)._eq('title', 'Post 2').build()

    BaseDao.execute_query(delete_builder, lazyload=True)
    users = BaseDao.all(User)
    print(f"Get all users and posts after delete")
    for user in users:
        print(f"> User: {user.name}")
        for post in user.posts:
            print(f">  Post: {post.title}")
    print('App ended')

