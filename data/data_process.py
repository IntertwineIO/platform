import json

class MissingRequiredField(Exception):
    def __init__(self, field):
        self.message = 'Required field "{field}"" is missing.'.format(field=field)

class Problem(object):
    """Base class for problems

    Problems and the connections between them are global in that they
    don't vary by region or organization. However, the ratings of the
    connections DO vary by geo, organization, and problem context."""
    # todo: add db support

    def __init__(self, **kwargs):
        """Initialize the problem fields EXCEPT for connections.

        Inputs are key-value pairs based on the JSON problem schema,
        EXCEPT those specifying problem connections. Problem connections
        are established using the set_connections method."""
        name = kwargs.get('name', None)
        if name == None:
            raise MissingRequiredField("name")
        self.name = name.title()
        self.definition = None
        self.definition_url = None
        self.images = []
        self.drivers = []
        self.impacts = []
        self.broader = []
        self.narrower = []
        if len(kwargs) > 1:
            self.set_values(**kwargs)

    def __repr__(self):
        cname = self.__class__.__name__
        return '<{cname}: {name}>'.format(cname=cname, name=self.name)

    def set_values(self, **kwargs):
        """Sets the problem fields EXCEPT for name and connections.

        Inputs are key-value pairs based on the JSON problem schema,
        EXCEPT those specifying problem connections. This method is
        called by __init__, but is also used to set values on problems
        that were previously created."""
        self.definition = kwargs.get('definition', self.definition)
        self.definition_url = kwargs.get('definition_url', self.definition_url)

        # for now, just store urls for images
        # todo: store local copies of images and keep track of url,
        # photo credit, licensing info, and user who posted it
        self.images = kwargs.get('images', self.images)

    def set_connections(self, entities, **kwargs):
        """Sets the problem connections and problem connection ratings.

        Inputs are key-value pairs describing problem connections, as
        defined by the JSON problem schema. The valid parameter names
        are the four problem connection types:

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
        the perceived importance of A as a driver of B.
        """

        # For each problem_connection, check if problem already exists.
        # If not, create it, setting the name and back-connection only.
        problems = entities['problems']

        for problem_connection in kwargs.get('drivers', []):
            adjacent_problem_name = problem_connection.get("adjacent_problem", None)
            if adjacent_problem_name == None:
                raise MissingRequiredField("adjacent_problem_name")
            adjacent_problem = problems.get(adjacent_problem_name.lower(), None)
            if not adjacent_problem:
                adjacent_problem = Problem(problems=problems, name=adjacent_problem_name)
                problems[adjacent_problem_name.lower()] = adjacent_problem
            self.drivers.append(adjacent_problem)
            adjacent_problem.impacts.append(self)
            # todo: add problem connections and ratings

        for problem_connection in kwargs.get('impacts', []):
            adjacent_problem_name = problem_connection.get("adjacent_problem", None)
            if adjacent_problem_name == None:
                raise MissingRequiredField("adjacent_problem_name")
            adjacent_problem = problems.get(adjacent_problem_name.lower(), None)
            if not adjacent_problem:
                adjacent_problem = Problem(problems=problems, name=adjacent_problem_name)
                problems[adjacent_problem_name.lower()] = adjacent_problem
            self.impacts.append(adjacent_problem)
            adjacent_problem.drivers.append(self)
            # todo: add problem connections and ratings

        # todo: add broader connections
        # todo: add narrower connections


def decode(json_data_path):
    """Loads JSON files within a path and returns data structures

    Returns a dictionary in which the keys are plural forms of the
    objects defined by the JSON problem schema, and the values are
    dictionaries containing each object type.

    Usage:
    >>> json_path = '/data/problems/problems.json'
    >>> data = decode(json_path)
    >>> problems = data["problems"]
    >>> p = problems["homelessness"]
    >>> connections = data["connections"]
    """

    # todo: ability to read in all json files in a directory
    with open(json_data_path) as json_file:
        # May need to change this to load incrementally in the future
        json_data = json.load(json_file)

    # todo: determine object type to be decoded, based on directory name
    entities = {
        'problems': {},
        # 'connections': {}
        }
    for key in json_data.keys():
        problem = entities['problems'].get(key.lower(), None)

        if not problem:
            problem = Problem(**json_data[key])
            entities['problems'][key.lower()] = problem
        else:
            problem.set_values(**json_data[key])

        problem.set_connections(entities=entities, **json_data[key])

    return entities

