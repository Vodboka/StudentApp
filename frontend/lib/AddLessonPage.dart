// ignore_for_file: file_names

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'LessonsPage.dart';

class LessonPage extends StatefulWidget {
  final String testText;

  LessonPage({required this.testText});

  @override
  _LessonPageState createState() => _LessonPageState();
}

class _LessonPageState extends State<LessonPage> {
  final TextEditingController _lessonNameController = TextEditingController();
  final TextEditingController _subjectController = TextEditingController();

  DateTime? _selectedDate;
  String? _selectedDifficulty;
  String? _selectedSubject;

  List<String> existingSubjects = [];
  late Future<List<String>> _subjectsFuture;

  final List<String> difficulties = ["Easy", "Medium", "Hard"];

  @override
  void initState() {
    super.initState();
    _subjectsFuture = fetchSubjects();
  }

  Future<List<String>> fetchSubjects() async {
    final response = await http.get(Uri.parse('http://10.0.2.2:5000/get_subjects'));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return List<String>.from(data['subjects']);
    } else {
      throw Exception('Failed to load subjects');
    }
  }

  Future<void> submitLesson() async {
    final String lessonName = _lessonNameController.text.trim();
    final String? difficulty = _selectedDifficulty;
    final DateTime? testDate = _selectedDate;
    final String subject = _subjectController.text.trim();

    if (lessonName.isEmpty || difficulty == null || testDate == null || subject.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Please fill in all fields")),
      );
      return;
    }

    // Show loading screen while submitting
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => LoadingScreen()));

    final Map<String, dynamic> lessonData = {
      'lesson_name': lessonName,
      'subject': subject,
      'date': testDate.toIso8601String(),
      'difficulty': difficulty,
      'text': widget.testText,
    };

    try {
      final url = 'http://10.0.2.2:5000/add_lesson';

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json; charset=utf-8'},
        body: utf8.encode(json.encode(lessonData)),
      );

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

      // Remove loading screen
      Navigator.of(context).pop();

      if (response.statusCode == 201) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Lesson saved successfully!")),
        );

        // Navigate to LessonsPage after submitting
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => LessonsPage(),
          ),
        );
      } else {
        final errorMsg = json.decode(response.body)['error'] ?? "Unknown error";
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error: $errorMsg")),
        );
      }
    } catch (e) {
      // Remove loading screen
      Navigator.of(context).pop();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Network error: ${e.toString()}")),
      );
    }
  }

  Future<void> _pickDate(BuildContext context) async {
    DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );

    if (pickedDate != null) {
      setState(() {
        _selectedDate = pickedDate;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Add Lesson Details")),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: FutureBuilder<List<String>>(
          future: _subjectsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return Center(child: CircularProgressIndicator());
            }

            if (snapshot.hasError) {
              return Center(child: Text('Failed to load subjects'));
            }

            if (snapshot.hasData) {
              existingSubjects = snapshot.data!;
            }

            return SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: _subjectController,
                    decoration: InputDecoration(
                      labelText: "Enter Subject Name",
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (text) {
                      setState(() {
                        _selectedSubject = text;
                      });
                    },
                  ),
                  SizedBox(height: 16),

                  // Display existing subjects if input is empty
                  if (_subjectController.text.isEmpty)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: existingSubjects
                          .map((subject) => ListTile(
                                title: Text(subject),
                                onTap: () {
                                  setState(() {
                                    _subjectController.text = subject;
                                  });
                                },
                              ))
                          .toList(),
                    ),
                  SizedBox(height: 16),

                  TextField(
                    controller: _lessonNameController,
                    decoration: InputDecoration(
                      labelText: "Lesson Name",
                      border: OutlineInputBorder(),
                    ),
                  ),
                  SizedBox(height: 16),

                  GestureDetector(
                    onTap: () => _pickDate(context),
                    child: AbsorbPointer(
                      child: TextField(
                        decoration: InputDecoration(
                          labelText: _selectedDate == null
                              ? "Select Test Date"
                              : "Test Date: ${_selectedDate!.toLocal().toIso8601String().split('T')[0]}",
                          border: OutlineInputBorder(),
                          suffixIcon: Icon(Icons.calendar_today),
                        ),
                      ),
                    ),
                  ),
                  SizedBox(height: 16),

                  DropdownButtonFormField<String>(
                    value: _selectedDifficulty,
                    decoration: InputDecoration(
                      labelText: "Difficulty Level",
                      border: OutlineInputBorder(),
                    ),
                    items: difficulties.map((String difficulty) {
                      return DropdownMenuItem<String>(
                        value: difficulty,
                        child: Text(difficulty),
                      );
                    }).toList(),
                    onChanged: (value) {
                      setState(() {
                        _selectedDifficulty = value;
                      });
                    },
                  ),
                  SizedBox(height: 24),

                  Center(
                    child: ElevatedButton(
                      onPressed: submitLesson,
                      child: Text("Submit"),
                    ),
                  ),
                  SizedBox(height: 16),
                  Text(
                    widget.testText,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[700],
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

// New loading screen widget
class LoadingScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Submitting Lesson"),
        automaticallyImplyLeading: false, // disable back button
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 20),
            Text("Please wait, submitting your lesson..."),
          ],
        ),
      ),
    );
  }
}
