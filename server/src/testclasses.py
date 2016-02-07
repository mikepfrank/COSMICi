# testclasses.py

class A:
    classVar = "A value."
    def go(this):
        print("I am class A.\n")

class B(A):
    classVar = "B value."
    def go(this):
        print("I am class B.\n")

def becomeClass(obj:object, newClass:type, *args, **kwargs):
    obj.__class__ = newClass
    newClass.__init__(obj, *args, **kwargs)

obj = A()
#obj.becomeClass = 
obj.becomeClass(B)
obj.go()
print(obj.classVar)
