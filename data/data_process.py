import json

class MissingRequiredField(Exception):
    def __init__(self, field, classname):
        msg = 'Required field "{!s}" on {!r} is missing.'.format(field, classname)
        self.message = msg

class FieldCollision(Exception):
    def __init__(self, field, entity):
        msg = 'Field "{!s}" on {!r} has already been set.'.format(field, entity)
        self.message = msg

class AsymmetricConnection(Exception):
    def __init__(self, problem_a, connected_type_a, problem_b, not_connected_type_b):
        msg = '{!r} defines {!r} as {!s}, '.format(problem_a, problem_b,
                                                   connected_type_a)
        msg += 'but {!r} does not define {!r} as {!s}.'.format(problem_b, problem_a,
                                                             not_connected_type_b)
        self.message = msg

class Problem(object):
    '''Base class for problems

    Problems and the connections between them are global in that they
    don't vary by region or organization. However, the ratings of the
    connections DO vary by geo, organization, and problem context.'''
    # todo: add db support

    # keeps track of all instances
    _registry = {}

    def __new__(cls, name, definition=None, definition_url=None, images=[],
                 drivers=[], impacts=[], broader=[], narrower=[]):
        """Create a new problem if it doesn't already existing

        Checks if a problem already exists with the given name in the
        _registry. If it does, return it with new=False. If it doesn't,
        create it and return it with new=True. The "new" attribute is
        used by __init__ to distinguish between new vs. existing
        problems.
        """
        key = name.title()
        problem = Problem._registry.get(key, None)
        if problem:
            problem.new = False
            return problem
        else:
            # todo: instead of calling object's __new__, call parent's __new__
            problem = object.__new__(cls, name, definition=None, definition_url=None, images=[])
            problem.new = True
            Problem._registry[key] = problem
            return problem

    def __init__(self, name, definition=None, definition_url=None, images=[],
                 drivers=[], impacts=[], broader=[], narrower=[]):
        '''Initialize a new problem or set fields on an existing problem

        Inputs are key-value pairs based on the JSON problem schema. If
        the problem is new, initialize the name and the other fields. If
        the problem already exists in the _registry, each field is set
        only if the corresponding input value is None or [] for lists. A
        FieldCollision exception is raised if the existing field and
        the input both have values (or len>0 for lists).

        The problem connection types are related to problems as follows:

                                   broader
                                      |
                        drivers -> problem -> impacts
                                      |
                                   narrower

        Problem connection ratings are input by users and are scoped by
        geo, organization, AND problem context. It is perfectly valid
        for the same user to provide a different rating of A -> B from
        the context of problem A vs. problem B because the perceived
        importance of B as an impact of A may be quite different from
        the perceived importance of A as a driver of B.'''

        if self.new:
            self.name = name.title()
            self.definition = definition
            self.definition_url = definition_url
            self.images = images
            self.drivers = []
            self.impacts = []
            self.broader = []
            self.narrower = []
        else:
            if definition:
                if not self.definition:
                    self.definition = definition
                else:
                    raise FieldCollision(field='definition', entity=self)
            if definition_url:
                if not self.definition_url:
                    self.definition_url = definition_url
                else:
                    raise FieldCollision(field='definition_url', entity=self)
            if len(images)>0:
                if len(self.images)==0:
                    self.images = images
                else:
                    raise FieldCollision('images', self)
        del self.new

        for problem_connection_data in drivers:
            adjacent_problem_name = problem_connection_data.get('adjacent_problem', None)
            if adjacent_problem_name == None:
                raise MissingRequiredField(field='adjacent_problem_name', classname='Problem')
            adjacent_problem_name = adjacent_problem_name.title()
            adjacent_problem = Problem(name=adjacent_problem_name)
            if adjacent_problem not in self.drivers:
                # print 'Adding {!r} as a driver of {!r}'.format(adjacent_problem, self)
                self.drivers.append(adjacent_problem)
                adjacent_problem.impacts.append(self)
            # else:
            #     print '{!r} is already a driver of {!r}'.format(adjacent_problem, self)

            # todo: add problem connections and ratings

        for problem_connection_data in impacts:
            adjacent_problem_name = problem_connection_data.get('adjacent_problem', None)
            if adjacent_problem_name == None:
                raise MissingRequiredField(field='adjacent_problem_name', classname='Problem')
            adjacent_problem_name = adjacent_problem_name.title()
            adjacent_problem = Problem(name=adjacent_problem_name)
            if adjacent_problem not in self.impacts:
                # print 'Adding {!r} as an impact of {!r}'.format(adjacent_problem, self)
                self.impacts.append(adjacent_problem)
                adjacent_problem.drivers.append(self)
            # else:
            #     print '{!r} is already an impact of {!r}'.format(adjacent_problem, self)

            # todo: add problem connections and ratings

        # todo: add broader connections
        # todo: add narrower connections

    def __repr__(self):
        cname = self.__class__.__name__
        return '<{cname!s}: {name!r}>'.format(cname=cname, name=self.name)

    def __str__(self):
        s = 'Problem: {!s}\n'.format(self.name)
        s += 'definition: {!s}\n'.format(self.definition)
        s += 'definition_url: {!s}\n'.format(self.definition_url)
        s += 'images:\n'
        for image in self.images:
            s += '    {!s}\n'.format(image)
        s += 'drivers:\n'
        for problem in self.drivers:
            s += '    {!s}\n'.format(problem.name)
        s += 'impacts:\n'
        for problem in self.impacts:
            s += '    {!s}\n'.format(problem.name)
        s += 'broader:\n'
        for problem in self.broader:
            s += '    {!s}\n'.format(problem.name)
        s += 'narrower:\n'
        for problem in self.narrower:
            s += '    {!s}\n'.format(problem.name)
        return s

def decode_problems(problem_name, problem_data):
    pass

def decode(json_data_path):
    '''Loads JSON files within a path and returns data structures

    Returns a dictionary in which the keys are plural forms of the
    objects defined by the JSON problem schema, and the values are
    dictionaries containing each object type.

    Usage:
    >>> json_path = '/data/problems/problems.json'
    >>> data = decode(json_path)
    >>> problems = data['problems']
    >>> p = problems['Homelessness']
    >>> connections = data['connections']
    '''

    # todo: ability to read in all json files in a directory
    with open(json_data_path) as json_file:
        # May need to change this to load incrementally in the future
        data = json.load(json_file)

    # todo: determine object type to be decoded, based on directory name
    entities = {
        'problems': {},
        # 'connections': {}
        }
    for problem_name, problem_data in data.items():
        problem_name = problem_name.title()

        problem = Problem(name=problem_name,
                          definition=problem_data.get('definition', None),
                          definition_url=problem_data.get('definition_url', None),
                          images=problem_data.get('images', []),
                          drivers=problem_data.get('drivers', []),
                          impacts=problem_data.get('impacts', []),
                          broader=problem_data.get('broader', []),
                          narrower=problem_data.get('narrower', []))

    entities['problems'] = Problem._registry
    return entities
