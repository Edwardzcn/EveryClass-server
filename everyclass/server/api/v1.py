import functools

from flask import jsonify, request, abort
from flask import current_app as app
import elasticapm

from everyclass.server.api import api_v1


def auth_required(func):
    """decorator for view functions that requires apikey authentication"""

    # 必须使用 functools.wraps 装饰器，否则 flask 会报错（函数同名（auth_required）导致一个 endpoint 于多个 url 注册）
    @functools.wraps(func)
    def wrapper(*args, **kw):
        # check if api is valid
        if request.authorization \
                and {'user': request.authorization.username,
                     'apikey': request.authorization.password} in app.config['API_CLIENTS']:
            return func(*args, **kw)
        else:
            return abort(403)

    return wrapper


@api_v1.route('/students/<student_id>')
@auth_required
def get_semesters(student_id):
    """
    提供学号，返回一个学生可用的学期。

    :param student_id: 学号
    """
    from everyclass.server.db.dao import get_my_semesters

    # todo: handle if student doesn't exist
    semesters, student_name = get_my_semesters(student_id)

    # Elastic apm 业务 context
    elasticapm.set_custom_context(stu_id=student_id)

    response = jsonify({'name': student_name,
                        'semesters': [s.to_str() for s in semesters]
                        })
    return response


@api_v1.route('/students/<student_id>/semesters/<semester>/courses')
@auth_required
def get_courses(student_id, semester):
    """
    提供学号与学期，返回学生当前学期的课表。

    :param student_id: 学号
    :param semester: 学期
    """
    import json
    from everyclass.server.db.dao import get_classes_for_student
    from everyclass.server.db.model import Semester
    from everyclass.server.exceptions import IllegalSemesterException, NoStudentException

    try:
        courses = get_classes_for_student(student_id, Semester(semester))
        # TODO: handle if semester does not exist

        elasticapm.set_custom_context(stu_id=student_id, semester=semester)

        courses_to_return = {}
        for k, v in courses.items():
            if str(k[0]) not in courses_to_return:
                courses_to_return[str(k[0])] = {}
            courses_to_return[str(k[0])][str(k[1])] = v
        return json.dumps({'courses': courses_to_return})
    except IllegalSemesterException:
        response = jsonify({'error': 'wrong semester'})
        response.status_code = 400
        return response
    except NoStudentException:
        response = jsonify({'error': 'no such student'})
        response.status_code = 400
        return response


@api_v1.errorhandler(403)
def error_handler_403(error):
    """handle resource not found error"""
    response = jsonify({'error': 'forbidden'})
    response.status_code = 403
    return response


@api_v1.errorhandler(500)
def error_handler_500(error):
    """handle 500 error"""
    response = jsonify({'error': 'server internal error'})
    response.status_code = 500
    return response
