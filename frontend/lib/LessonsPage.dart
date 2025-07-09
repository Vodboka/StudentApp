// ignore_for_file: file_names
// TODO sort the lessons for each subject by: Test date and afterwards by difficulty
//TODO display the subject by the test dates
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:test_application/LessonCirclesPage.dart'; // Ensure this import is correct
import 'package:intl/intl.dart'; // Import for date formatting. Make sure 'intl' is in your pubspec.yaml!


class LessonsPage extends StatefulWidget {
  @override
  _LessonsPageState createState() => _LessonsPageState();
}

class _LessonsPageState extends State<LessonsPage> {
  // New state variables for grouped lessons
  Map<String, List<Map<String, dynamic>>> _groupedLessons = {};
  List<String> _subjects = []; // To maintain the order of subjects for display

  bool isLoading = true;
  bool hasError = false;

  @override
  void initState() {
    super.initState();
    fetchLessons();
  }

  Future<void> fetchLessons() async {
    try {
      final response = await http.get(Uri.parse('http://10.0.2.2:5000/get_lessons'));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        List<Map<String, dynamic>> fetchedLessons = List<Map<String, dynamic>>.from(data['lessons']);

        Map<String, List<Map<String, dynamic>>> tempGroupedLessons = {};
        List<String> tempSubjects = [];

        // Group lessons by subject
        for (var lesson in fetchedLessons) {
          final subject = lesson['subject'] as String? ?? 'Uncategorized'; // Handle potential null subject
          if (!tempGroupedLessons.containsKey(subject)) {
            tempGroupedLessons[subject] = [];
            tempSubjects.add(subject); // Add subject to our ordered list
          }
          tempGroupedLessons[subject]!.add(lesson);
        }

        // Sort subjects alphabetically for consistent display
        tempSubjects.sort();

        setState(() {
          _groupedLessons = tempGroupedLessons;
          _subjects = tempSubjects;
          isLoading = false;
          hasError = false; // Reset error state on successful fetch
        });
      } else {
        throw Exception('Failed to load lessons with status: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching lessons: $e'); // Debugging
      setState(() {
        isLoading = false;
        hasError = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    double screenHeight = MediaQuery.of(context).size.height;

    return Scaffold(
      appBar: AppBar(title: Text("Lessons")),
      body: Padding(
        padding: const EdgeInsets.all(0.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Info message if no lessons are present (after loading)
            if (!isLoading && !hasError && _groupedLessons.isEmpty)
              Padding(
                padding: EdgeInsets.only(top: screenHeight * 0.01, bottom: 10.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.start,
                  children: [
                    Icon(Icons.arrow_back, size: 20, color: Colors.deepOrange),
                    SizedBox(width: 5),
                    Flexible(
                      child: Text(
                        "Check whether there are any materials to work on!",
                        style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
                      ),
                    ),
                  ],
                ),
              ),

            // Loading indicator
            if (isLoading)
              Expanded(child: Center(child: CircularProgressIndicator()))
            
            // Error message
            else if (hasError)
              Expanded(
                child: Center(
                  child: Text(
                    "Failed to load lessons. Please try again later.",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
                    textAlign: TextAlign.center,
                  ),
                ),
              )
            
            // "No lessons created yet" message (if loaded and empty)
            else if (_groupedLessons.isEmpty) // Check the grouped map now
              Expanded(
                child: Center(
                  child: Padding(
                    padding: EdgeInsets.only(top: screenHeight * 0.1),
                    child: Text(
                      "No lessons created yet",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              )

            // Display grouped lessons
            else
              Expanded(
                child: ListView.builder(
                  itemCount: _subjects.length, // Iterate over subjects
                  itemBuilder: (context, subjectIndex) {
                    final subject = _subjects[subjectIndex];
                    final lessonsInSubject = _groupedLessons[subject]!; // Get list of lessons for this subject

                    return Card( // Wrap ExpansionTile in a Card for consistent styling
                      margin: EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
                      elevation: 3,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12.0),
                      ),
                      clipBehavior: Clip.antiAlias, // Ensures content respects rounded corners
                      child: Theme( // <<<< MODIFIED: Wrap with Theme to control dividerColor >>>>
                        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                        child: ExpansionTile(
                          title: Text(
                            subject,
                            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                          ),
                          // Removed collapsedShape and expandedShape as they are not defined in older Flutter versions
                          childrenPadding: EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                          children: lessonsInSubject.map((lesson) {
                            final lessonNamehere = lesson['lesson_name'] ?? 'Untitled';
                            final dateString = lesson['date'] ?? 'Unknown'; // Get the date string
                            final difficulty = lesson['difficulty'] ?? 'N/A';

                            // Format the date for better readability
                            String formattedDate = 'Unknown';
                            try {
                              // Assuming dateString is in a format like 'YYYY-MM-DD'
                              final dateTime = DateTime.parse(dateString);
                              formattedDate = DateFormat('MMMM d,yyyy').format(dateTime); // e.g., "June 3, 2025"
                            } catch (e) {
                              print('Error parsing date: $dateString - $e');
                              formattedDate = 'Invalid Date';
                            }

                            return GestureDetector(
                              onTap: () async {
                                final uri = Uri.parse('http://10.0.2.2:5000/get_lesson_hash').replace(queryParameters: {
                                  'lesson_name': lessonNamehere,
                                  'subject': lesson['subject'],
                                });

                                try {
                                  final response = await http.get(uri);

                                  if (response.statusCode == 200) {
                                    final data = json.decode(response.body);
                                    final hash = data['lesson hash'];

                                    Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) => LessonCirclesPage(
                                          hash: hash,
                                        ),
                                      ),
                                    );
                                  } else {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text("Lesson hash not found")),
                                    );
                                  }
                                } catch (e) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text("Failed to fetch lesson hash")),
                                  );
                                }
                              },
                              child: Card( // Inner Card for each lesson
                                margin: EdgeInsets.symmetric(vertical: 4.0),
                                elevation: 1, // Slightly less elevation than the subject card
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(8.0),
                                ),
                                child: Padding(
                                  padding: const EdgeInsets.all(12.0),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        lessonNamehere,
                                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                                      ),
                                      SizedBox(height: 6),
                                      LayoutBuilder(
                                        builder: (context, constraints) {
                                          bool isNarrow = constraints.maxWidth < 250; // Adjust narrow threshold

                                          return Wrap(
                                            alignment: WrapAlignment.spaceBetween,
                                            spacing: 8,
                                            runSpacing: 4,
                                            direction: isNarrow ? Axis.vertical : Axis.horizontal,
                                            children: [
                                              // Use the formattedDate here
                                              Text("Test Date: $formattedDate", style: TextStyle(fontSize: 14)),
                                              Text("Difficulty: $difficulty", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
                                            ],
                                          );
                                        },
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          }).toList(), // Convert the map result to a list of widgets
                        ),
                      ), // <<<< END MODIFIED: Closing Theme widget >>>>
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}
