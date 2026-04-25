from django.db import models
from django.utils import timezone


# Store the library users who can borrow and return books.
class LibraryUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    # Show the user's name in Django admin and debug output.
    def __str__(self):
        return self.name


# Store each book in the library catalog and its inventory count.
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    # Show a readable book label in admin and logs.
    def __str__(self):
        return f"{self.title} - {self.author}"


# Store one borrowing record that connects a user and a book.
class Loan(models.Model):
    user = models.ForeignKey(LibraryUser, on_delete=models.CASCADE, related_name="loans")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="loans")
    borrowed_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["returned_at", "due_date", "-borrowed_at"]

    # Show a readable borrowing relationship in admin and logs.
    def __str__(self):
        return f"{self.user} -> {self.book}"

    @property
    # Mark whether this loan has been returned already.
    def is_returned(self):
        return self.returned_at is not None

    @property
    # A loan is overdue only when it is still active and the due date has passed.
    def is_overdue(self):
        return not self.is_returned and self.due_date < timezone.localdate()
